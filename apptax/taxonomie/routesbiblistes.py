# coding: utf8

import os
import logging
import pdb

from flask import Blueprint, request, current_app
from sqlalchemy import func, or_
from sqlalchemy.orm import aliased

from pypnusershub import routes as fnauth

from . import filemanager
from . import db
from ..log import logmanager
from ..utils.utilssqlalchemy import json_resp, csv_resp
from ..utils.genericfunctions import calculate_offset_page
from .models import BibListes, CorNomListe, Taxref, BibNoms, BibTaxrefHabitats, TMedias, CorTaxonAttribut


adresses = Blueprint("bib_listes", __name__)
logger = logging.getLogger()


@adresses.route("/", methods=["GET"])
@json_resp
def get_biblistes(id=None):
    """
    retourne les contenu de bib_listes dans "data"
    et le nombre d'enregistrements dans "count"
    """
    data = (
        db.session.query(BibListes, func.count(CorNomListe.id_nom).label("c"))
        .outerjoin(CorNomListe)
        .group_by(BibListes)
        .order_by(BibListes.nom_liste)
        .all()
    )
    maliste = {"data": [], "count": 0}
    maliste["count"] = len(data)
    for l in data:
        d = l.BibListes.as_dict()
        d["nb_taxons"] = l.c
        maliste["data"].append(d)
    return maliste


@adresses.route("/<regne>", methods=["GET"])
@adresses.route("/<regne>/<group2_inpn>", methods=["GET"])
@json_resp
def get_biblistesbyTaxref(regne, group2_inpn=None):
    q = db.session.query(BibListes)
    if regne:
        q = q.filter(or_(BibListes.regne == regne, BibListes.regne == None))
    if group2_inpn:
        q = q.filter(or_(BibListes.group2_inpn == group2_inpn, BibListes.group2_inpn == None))
    results = q.all()
    return [liste.as_dict() for liste in results]


@adresses.route("/exportcsv/<int:idliste>", methods=["GET"])
@csv_resp
def getExporter_biblistesCSV(idliste=None):
    """
    Exporter les taxons d'une liste dans un fichier csv
    """
    liste = db.session.query(BibListes).get(idliste)
    cleanNomliste = filemanager.removeDisallowedFilenameChars(liste.nom_liste)

    data = (
        db.session.query(Taxref)
        .filter(BibNoms.cd_nom == Taxref.cd_nom)
        .filter(BibNoms.id_nom == CorNomListe.id_nom)
        .filter(CorNomListe.id_liste == idliste)
        .all()
    )
    return (
        cleanNomliste,
        [nom.as_dict() for nom in data],
        Taxref.__table__.columns.keys(),
        ",",
    )


# ######## Route pour module edit and create biblistes ############


# Get data of list by id
@adresses.route("/<int:idliste>", methods=["GET"])
@json_resp
def getOne_biblistes(idliste=None):
    data = db.session.query(BibListes).filter_by(id_liste=idliste).first()
    return data.as_dict()


# Get list of picto in repertory ./static/images/pictos
@adresses.route("/pictosprojet", methods=["GET"])
@json_resp
def getPictos_files():
    pictos = os.listdir(os.path.join(current_app.static_folder, "images/pictos"))

    pictos.sort()
    return pictos


# ######## PUT CREER/MODIFIER BIBLISTES ######################
@adresses.route("/", methods=["POST", "PUT"])
@adresses.route("/<int:id_liste>", methods=["POST", "PUT"])
@json_resp
@fnauth.check_auth(4, True)
def insertUpdate_biblistes(id_liste=None, id_role=None):
    res = request.get_json(silent=True)
    data = {k: v or None for (k, v) in res.items()}

    action = "INSERT"
    message = "Liste créée"
    if id_liste:
        action = "UPDATE"
        message = "Liste mise à jour"

    bib_liste = BibListes(**data)
    db.session.merge(bib_liste)
    db.session.commit()
    logmanager.log_action(
        id_role, "bib_liste", bib_liste.id_liste, repr(bib_liste), action, message
    )
    return bib_liste.as_dict()


# ####### Route pour module ajouter noms à la liste ##########################
#  Get Taxons + taxref in a liste with id_liste
@adresses.route("/taxons/<int:idliste>", methods=["GET"])
@json_resp
def getNoms_bibtaxons(idliste):
    # Traitement des parametres
    parameters = request.args
    limit = parameters.get("limit", 100, int)
    page = parameters.get("page", 1, int)
    offset = parameters.get("offset", 0, int)
    (limit, offset, page) = calculate_offset_page(limit, offset, page)

    # Récupération du groupe de la liste
    (regne, group2_inpn) = (
        db.session.query(BibListes.regne, BibListes.group2_inpn)
        .filter(BibListes.id_liste == idliste)
        .one()
    )

    CorTaxonAttribut100 = aliased(CorTaxonAttribut, name='CorTaxonAttribut100')
    CorTaxonAttribut101 = aliased(CorTaxonAttribut, name='CorTaxonAttribut101')
    CorTaxonAttribut102 = aliased(CorTaxonAttribut, name='CorTaxonAttribut102')
    CorTaxonAttribut103 = aliased(CorTaxonAttribut, name='CorTaxonAttribut103')
    CorTaxonAttribut104 = aliased(CorTaxonAttribut, name='CorTaxonAttribut104')
    CorTaxonAttribut105 = aliased(CorTaxonAttribut, name='CorTaxonAttribut105')

    q = db.session.query(
    BibNoms.id_nom,
    BibNoms.cd_nom,
    BibNoms.cd_ref,
    BibNoms.nom_francais,
    Taxref.famille,
    Taxref.nom_complet,
    Taxref.regne,
    Taxref.group1_inpn,
    Taxref.group2_inpn,
    Taxref.id_rang,
    Taxref.id_habitat,
    BibTaxrefHabitats.nom_habitat,
    TMedias.chemin,
    CorTaxonAttribut100.valeur_attribut.label('atlas_description'),
    CorTaxonAttribut101.valeur_attribut.label('atlas_biogeographie'),
    CorTaxonAttribut102.valeur_attribut.label('atlas_milieu'),
    CorTaxonAttribut103.valeur_attribut.label('atlas_habitats_lies'),
    CorTaxonAttribut104.valeur_attribut.label('atlas_invasibilite'),
    CorTaxonAttribut105.valeur_attribut.label('reglementation_eee')
).join(
    Taxref, BibNoms.cd_nom == Taxref.cd_nom
).join(
    BibTaxrefHabitats, BibTaxrefHabitats.id_habitat == Taxref.id_habitat
).outerjoin(
    TMedias, (TMedias.cd_ref == Taxref.cd_ref) & (TMedias.id_type == 1)
    ).outerjoin(CorTaxonAttribut100, (CorTaxonAttribut100.cd_ref == Taxref.cd_ref) & (CorTaxonAttribut100.id_attribut == 100)
    ).outerjoin(CorTaxonAttribut101, (CorTaxonAttribut101.cd_ref == Taxref.cd_ref) & (CorTaxonAttribut101.id_attribut == 101)
    ).outerjoin(CorTaxonAttribut102, (CorTaxonAttribut102.cd_ref == Taxref.cd_ref) & (CorTaxonAttribut102.id_attribut == 102)
    ).outerjoin(CorTaxonAttribut103, (CorTaxonAttribut103.cd_ref == Taxref.cd_ref) & (CorTaxonAttribut103.id_attribut == 103)
    ).outerjoin(CorTaxonAttribut104, (CorTaxonAttribut104.cd_ref == Taxref.cd_ref) & (CorTaxonAttribut104.id_attribut == 104)
    ).outerjoin(CorTaxonAttribut105, (CorTaxonAttribut105.cd_ref == Taxref.cd_ref) & (CorTaxonAttribut105.id_attribut == 105))

    if regne:
        q = q.filter(or_(Taxref.regne == regne))
    if group2_inpn:
        q = q.filter(or_(Taxref.group2_inpn == group2_inpn))

    subq = db.session.query(CorNomListe.id_nom).filter(CorNomListe.id_liste == idliste).subquery()

    if parameters.get("existing"):
        q = q.join(subq, subq.c.id_nom == BibNoms.id_nom)
    else:
        q = q.outerjoin(subq, subq.c.id_nom == BibNoms.id_nom).filter(subq.c.id_nom == None)
    nbResultsWithoutFilter = q.count()
    if parameters.get("cd_nom"):
        try:
            q = q.filter(BibNoms.cd_nom == int(parameters.get("cd_nom")))
        except Exception:
            pass
    if parameters.get("nom_francais"):
        q = q.filter(BibNoms.nom_francais.ilike(parameters.get("nom_francais") + "%"))
    if parameters.get("nom_complet"):
        q = q.filter(Taxref.nom_complet.ilike(parameters.get("nom_complet") + "%"))
    if parameters.get("id_rang"):
        q = q.filter(Taxref.id_rang.ilike(parameters.get("id_rang") + "%"))

    # Order by
    bibTaxonColumns = BibNoms.__table__.columns
    taxrefColumns = Taxref.__table__.columns
    if "orderby" in parameters:
        if parameters["orderby"] in taxrefColumns:
            orderCol = getattr(taxrefColumns, parameters["orderby"])
        elif parameters["orderby"] in bibTaxonColumns:
            orderCol = getattr(bibTaxonColumns, parameters["orderby"])
        else:
            orderCol = None

        if "order" in parameters:
            if parameters["order"] == "desc":
                orderCol = orderCol.desc()

        q = q.order_by(orderCol)

    nbResults = q.count()
    data = q.limit(limit).offset(offset).all()

    results = []
    for row in data:
        data_as_dict = {}
        data_as_dict["id_nom"] = row.id_nom
        data_as_dict["cd_nom"] = row.cd_nom
        data_as_dict["cd_ref"] = row.cd_ref
        data_as_dict["famille"] = row.famille
        data_as_dict["nom_francais"] = row.nom_francais
        data_as_dict["nom_complet"] = row.nom_complet
        data_as_dict["regne"] = row.regne
        data_as_dict["group1_inpn"] = row.group1_inpn
        data_as_dict["group2_inpn"] = row.group2_inpn
        data_as_dict["habitat"] = row.nom_habitat
        data_as_dict["id_rang"] = row.id_rang
        data_as_dict["path_main_picture"] = row.chemin
        data_as_dict["atlas_description"] = row.atlas_description
        data_as_dict["atlas_biogeographie"] = row.atlas_biogeographie
        data_as_dict["atlas_milieu"] = row.atlas_milieu
        data_as_dict["atlas_habitats_lies"] = row.atlas_habitats_lies
        data_as_dict["atlas_invasibilite"] = row.atlas_invasibilite
        data_as_dict["reglementation_eee"] = row.reglementation_eee
        results.append(data_as_dict)

    return {
        "items": results,
        "total": nbResultsWithoutFilter,
        "total_filtered": nbResults,
        "limit": limit,
        "page": page,
    }


# POST - Ajouter les noms à une liste
@adresses.route("/addnoms/<int:idliste>", methods=["POST"])
@json_resp
@fnauth.check_auth(4, True)
def add_cornomliste(idliste=None, id_role=None):
    ids_nom = request.get_json(silent=True)

    # TODO add test if idlist exists

    for id in ids_nom:
        cornom = {"id_nom": id, "id_liste": idliste}
        add_nom = CorNomListe(**cornom)
        db.session.add(add_nom)
    db.session.commit()

    logmanager.log_action(
        id_role, "cor_nom_liste", idliste, "", "AJOUT NOM", "Noms ajouté à la liste"
    )
    return ids_nom


# POST - Enlever les nom dans une liste
@adresses.route("/deletenoms/<int:idliste>", methods=["POST"])
@json_resp
@fnauth.check_auth(4, True)
def delete_cornomliste(idliste=None, id_role=None):
    ids_nom = request.get_json(silent=True)
    for id in ids_nom:
        del_nom = (
            db.session.query(CorNomListe)
            .filter(CorNomListe.id_liste == idliste)
            .filter(CorNomListe.id_nom == id)
            .first()
        )
        db.session.delete(del_nom)
    db.session.commit()
    logmanager.log_action(
        id_role,
        "cor_nom_liste",
        idliste,
        "",
        "SUPPRESSION NOM",
        "Noms supprimés de la liste",
    )

    return ids_nom
