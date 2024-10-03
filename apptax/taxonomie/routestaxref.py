from warnings import warn

from flask import abort, jsonify, Blueprint, request
from sqlalchemy import distinct, desc, func, and_
from sqlalchemy.orm.exc import NoResultFound


from ..utils.utilssqlalchemy import json_resp, serializeQuery, serializeQueryOneResult
from .models import (
    Taxref,
    BibNoms,
    VMTaxrefListForautocomplete,
    BibTaxrefHabitats,
    BibTaxrefRangs,
    BibTaxrefStatus,
    VMTaxrefHierarchie,
    VTaxrefHierarchieBibtaxons,
    BibTaxrefHabitats,
    CorNomListe,
    BibListes,
)

from .repositories import BdcStatusRepository

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from . import db

adresses = Blueprint("taxref", __name__)


@adresses.route("/", methods=["GET"])
@json_resp
def getTaxrefList():
    return genericTaxrefList(False, request.args)


@adresses.route("/bibnoms/", methods=["GET"])
@json_resp
def getTaxrefBibtaxonList():
    return genericTaxrefList(True, request.args)


@adresses.route("/search/<field>/<ilike>", methods=["GET"])
def getSearchInField(field, ilike):
    """.. http:get:: /taxref/search/(str:field)/(str:ilike)
    .. :quickref: Taxref;

    Retourne les 20 premiers résultat de la table "taxref" pour une
    requête sur le champ `field` avec ILIKE et la valeur `ilike` fournie.
    L'algorithme Trigramme est utilisé pour établir la correspondance.

    :query fields: Permet de récupérer des champs suplémentaire de la
        table "taxref" dans la réponse. Séparer les noms des champs par
        des virgules.
    :query is_inbibnom: Ajoute une jointure sur la table "bib_noms".
    :query add_rank: Ajoute une jointure sur la table "bib_taxref_rangs"
        et la colonne nom_rang aux résultats.
    :query rank_limit: Retourne seulement les taxons dont le rang est
        supérieur ou égal au rang donné. Le rang passé doit être une
        valeur de la colonne "id_rang" de la table "bib_taxref_rangs".

    :statuscode 200: Tableau de dictionnaires correspondant aux résultats
        de la recherche dans la table "taxref".
    :statuscode 500: Aucun rang ne correspond à la valeur fournie.
                     Aucune colonne ne correspond à la valeur fournie.
    """
    taxrefColumns = Taxref.__table__.columns
    if field in taxrefColumns:
        value = unquote(ilike)
        value = value.replace(" ", "%")
        column = taxrefColumns[field]
        q = (
            db.session.query(
                column,
                Taxref.cd_nom,
                Taxref.cd_ref,
                func.similarity(column, value).label("idx_trgm"),
            )
            .filter(column.ilike("%" + value + "%"))
            .order_by(desc("idx_trgm"))
        )

        if request.args.get("fields"):
            fields = request.args["fields"].split(",")
            for field in fields:
                if field in taxrefColumns:
                    column = taxrefColumns[field]
                    q = q.add_columns(column)
                else:
                    msg = f"No column found in Taxref for {field}"
                    return jsonify(msg), 500

        if request.args.get("is_inbibnoms"):
            q = q.join(BibNoms, BibNoms.cd_nom == Taxref.cd_nom)
        join_on_bib_rang = False
        if request.args.get("add_rank"):
            q = q.join(BibTaxrefRangs, Taxref.id_rang == BibTaxrefRangs.id_rang)
            q = q.add_columns(BibTaxrefRangs.nom_rang)
            join_on_bib_rang = True

        if "rank_limit" in request.args:
            if not join_on_bib_rang:
                q = q.join(BibTaxrefRangs, Taxref.id_rang == BibTaxrefRangs.id_rang)
            try:
                sub_q_id_rang = (
                    db.session.query(BibTaxrefRangs.tri_rang)
                    .filter(BibTaxrefRangs.id_rang == request.args["rank_limit"])
                    .one()
                )
            except NoResultFound:
                return (
                    jsonify("No rank found for {}".format(request.args["rank_limit"])),
                    500,
                )
            q = q.filter(BibTaxrefRangs.tri_rang <= sub_q_id_rang[0])

        results = q.limit(20).all()
        return jsonify(serializeQuery(results, q.column_descriptions))
    else:
        jsonify("No column found in Taxref for {}".format(field)), 500


@adresses.route("/<int(signed=True):id>", methods=["GET"])
def getTaxrefDetail(id):
    dfCdNom = Taxref.__table__.columns["cd_nom"]

    q = (
        db.session.query(
            Taxref.cd_nom,
            Taxref.cd_ref,
            Taxref.regne,
            Taxref.phylum,
            Taxref.classe,
            Taxref.ordre,
            Taxref.famille,
            Taxref.cd_taxsup,
            Taxref.cd_sup,
            Taxref.cd_taxsup,
            Taxref.nom_complet,
            Taxref.nom_valide,
            Taxref.nom_vern,
            Taxref.group1_inpn,
            Taxref.group2_inpn,
            Taxref.id_rang,
            BibTaxrefRangs.nom_rang,
            BibTaxrefStatus.nom_statut,
            BibTaxrefHabitats.nom_habitat,
        )
        .outerjoin(BibTaxrefHabitats, BibTaxrefHabitats.id_habitat == Taxref.id_habitat)
        .outerjoin(BibTaxrefStatus, BibTaxrefStatus.id_statut == Taxref.id_statut)
        .outerjoin(BibTaxrefRangs, BibTaxrefRangs.id_rang == Taxref.id_rang)
        .filter(dfCdNom == id)
    )

    results = q.one()

    taxon = serializeQueryOneResult(results, q.column_descriptions)

    qsynonymes = db.session.query(Taxref.cd_nom, Taxref.nom_complet).filter(
        Taxref.cd_ref == results.cd_ref
    )

    synonymes = qsynonymes.all()

    taxon["synonymes"] = [
        {c: getattr(row, c) for c in ["cd_nom", "nom_complet"] if getattr(row, c) is not None}
        for row in synonymes
    ]

    areas = None
    if request.args.get("areas_status"):
        areas = request.args["areas_status"].split(",")

    areas_code = None
    if request.args.get("areas_code_status"):
        areas_code = request.args["areas_code_status"].split(",")

    taxon["status"] = BdcStatusRepository().get_status(
        cd_ref=results.cd_ref, areas=areas, areas_code=areas_code, type_statut=None, format=True
    )

    return jsonify(taxon)


@adresses.route("/distinct/<field>", methods=["GET"])
def getDistinctField(field):
    taxrefColumns = Taxref.__table__.columns
    q = db.session.query(taxrefColumns[field]).distinct(taxrefColumns[field])

    limit = request.args.get("limit", 100, int)

    for param in request.args:
        if param in taxrefColumns:
            col = getattr(taxrefColumns, param)
            q = q.filter(col == request.args[param])
        elif param == "ilike":
            q = q.filter(taxrefColumns[field].ilike(request.args[param] + "%"))

    results = q.limit(limit).all()
    return jsonify(serializeQuery(results, q.column_descriptions))


@adresses.route("/hierarchie/<rang>", methods=["GET"])
@json_resp
def getTaxrefHierarchie(rang):
    results = genericHierarchieSelect(VMTaxrefHierarchie, rang, request.args)
    return [r.as_dict() for r in results]


@adresses.route("/hierarchiebibtaxons/<rang>", methods=["GET"])
@json_resp
def getTaxrefHierarchieBibNoms(rang):
    results = genericHierarchieSelect(VTaxrefHierarchieBibtaxons, rang, request.args)
    return [r.as_dict() for r in results]


def genericTaxrefList(inBibtaxon, parameters):
    taxrefColumns = Taxref.__table__.columns
    bibNomsColumns = BibNoms.__table__.columns
    q = db.session.query(Taxref, BibNoms.id_nom)

    qcount = q.outerjoin(BibNoms, BibNoms.cd_nom == Taxref.cd_nom)

    nbResultsWithoutFilter = qcount.count()

    if inBibtaxon is True:
        q = q.join(BibNoms, BibNoms.cd_nom == Taxref.cd_nom)
    else:
        q = q.outerjoin(BibNoms, BibNoms.cd_nom == Taxref.cd_nom)

    # Traitement des parametres
    limit = parameters.get("limit", 20, int)
    page = parameters.get("page", 1, int)

    for param in parameters:
        if param in taxrefColumns and parameters[param] != "":
            col = getattr(taxrefColumns, param)
            q = q.filter(col == parameters[param])
        elif param == "is_ref" and parameters[param] == "true":
            q = q.filter(Taxref.cd_nom == Taxref.cd_ref)
        elif param == "ilike":
            q = q.filter(Taxref.lb_nom.ilike(parameters[param] + "%"))
        elif param == "is_inbibtaxons" and parameters[param] == "true":
            q = q.filter(bibNomsColumns.cd_nom.isnot(None))
        elif param.split("-")[0] == "ilike":
            value = unquote(parameters[param])
            col = str(param.split("-")[1])
            q = q.filter(taxrefColumns[col].ilike(value + "%"))

    nbResults = q.count()

    # Order by
    if "orderby" in parameters:
        if parameters["orderby"] in taxrefColumns:
            orderCol = getattr(taxrefColumns, parameters["orderby"])
        else:
            orderCol = None
        if "order" in parameters:
            if parameters["order"] == "desc":
                orderCol = orderCol.desc()
        q = q.order_by(orderCol)

    results = q.paginate(page=page, per_page=limit, error_out=False)
    return {
        "items": [dict(d.Taxref.as_dict(), **{"id_nom": d.id_nom}) for d in results.items],
        "total": nbResultsWithoutFilter,
        "total_filtered": nbResults,
        "limit": limit,
        "page": page,
    }


def genericHierarchieSelect(tableHierarchy, rang, parameters):
    dfRang = tableHierarchy.__table__.columns["id_rang"]
    q = db.session.query(tableHierarchy).filter(tableHierarchy.id_rang == rang)

    limit = parameters.get("limit", 100, int)

    for param in parameters:
        if param in tableHierarchy.__table__.columns:
            col = getattr(tableHierarchy.__table__.columns, param)
            q = q.filter(col == parameters[param])
        elif param == "ilike":
            q = q.filter(tableHierarchy.__table__.columns.lb_nom.ilike(parameters[param] + "%"))

    results = q.limit(limit).all()
    return results


@adresses.route("/regnewithgroupe2", methods=["GET"])
@json_resp
def get_regneGroup2Inpn_taxref():
    """
    Retourne la liste des règne et groupe 2
        défini par taxref de façon hiérarchique
    formatage : {'regne1':['grp1', 'grp2'], 'regne2':['grp3', 'grp4']}
    """
    q = (
        db.session.query(Taxref.regne, Taxref.group2_inpn)
        .distinct(Taxref.regne, Taxref.group2_inpn)
        .filter(Taxref.regne != None)
        .filter(Taxref.group2_inpn != None)
    )
    data = q.all()
    results = {"": [""]}
    for d in data:
        if d.regne in results:
            results[d.regne].append(d.group2_inpn)
        else:
            results[d.regne] = ["", d.group2_inpn]
    return results


@adresses.route("/allnamebylist/<string:code_liste>", methods=["GET"])
@adresses.route("/allnamebylist", methods=["GET"])
@json_resp
def get_AllTaxrefNameByListe(code_liste=None):
    """
    Route utilisée pour les autocompletes
    Si le paramètre search_name est passé, la requête SQL utilise l'algorithme
    des trigrames pour améliorer la pertinence des résultats
    Route utilisé par le mobile pour remonter la liste des taxons
    params URL:
        - code_liste : code de la liste (si id liste est null ou = à -1 on ne prend pas de liste)
    params GET (facultatifs):
        - search_name : nom recherché. Recherche basé sur la fonction
            ilike de sql avec un remplacement des espaces par %
        - regne : filtre sur le regne INPN
        - group2_inpn : filtre sur le groupe 2 de l'INPN
        - limit: nombre de résultat
        - offset: numéro de la page
    """
    # Traitement des cas ou code_liste = -1
    id_liste = None
    try:
        if code_liste:
            code_liste_to_int = int(code_liste)
            if code_liste_to_int == -1:
                id_liste = -1
        else:
            id_liste = -1
    except ValueError:
        # le code liste n'est pas un entier
        #   mais une chaine de caractère c-a-d bien un code
        pass

    # Get id_liste
    try:
        # S'il y a une id_liste elle à forcement la valeur -1
        #   c-a-d pas de liste
        if not id_liste:
            q = (
                db.session.query(BibListes.id_liste).filter(BibListes.code_liste == code_liste)
            ).one()
            id_liste = q[0]
    except NoResultFound:
        return (
            {"success": False, "message": "Code liste '{}' inexistant".format(code_liste)},
            400,
        )

    q = db.session.query(VMTaxrefListForautocomplete)
    if id_liste and id_liste != -1:
        q = q.join(BibNoms, BibNoms.cd_nom == VMTaxrefListForautocomplete.cd_nom).join(
            CorNomListe,
            and_(CorNomListe.id_nom == BibNoms.id_nom, CorNomListe.id_liste == id_liste),
        )

    search_name = request.args.get("search_name")
    if search_name:
        q = q.add_columns(
            func.similarity(VMTaxrefListForautocomplete.search_name, search_name).label("idx_trgm")
        )
        search_name = search_name.replace(" ", "%")
        q = q.filter(
            func.unaccent(VMTaxrefListForautocomplete.search_name).ilike(
                func.unaccent("%" + search_name + "%")
            )
        ).order_by(desc("idx_trgm"))
        q = q.order_by(
            desc(VMTaxrefListForautocomplete.cd_nom == VMTaxrefListForautocomplete.cd_ref)
        )
    # if no search name no need to order by trigram or cd_nom=cdref - order by PK (use for mobile app)
    else:
        q = q.order_by(VMTaxrefListForautocomplete.gid)

    regne = request.args.get("regne")
    if regne:
        q = q.filter(VMTaxrefListForautocomplete.regne == regne)

    group2_inpn = request.args.get("group2_inpn")
    if group2_inpn:
        q = q.filter(VMTaxrefListForautocomplete.group2_inpn == group2_inpn)

    limit = request.args.get("limit", 20, int)
    page = request.args.get("page", 1, int)
    if "offset" in request.args:
        warn(
            "offset is deprecated, please use page for pagination (start at 1)", DeprecationWarning
        )
        page = (int(request.args["offset"]) / limit) + 1
    data = q.paginate(page=page, per_page=limit, error_out=False)

    if search_name:
        return [d[0].as_dict() for d in data.items]
    else:
        return [d.as_dict() for d in data.items]


@adresses.route("/bib_habitats", methods=["GET"])
@json_resp
def get_bib_hab():
    data = db.session.query(BibTaxrefHabitats).all()
    return [d.as_dict() for d in data]


### Nouvelles fonctions réalisés pour la fonctionnalité d'ajout de taxons


@adresses.route("/addTaxon", methods=["POST"])
def add_taxon():
    """
    Route utilisée pour insérer un nouveau taxon en bdd
    params POST :
        - objet contenant toutes les données du taxon à ajouter en bdd.
        - save: boolean qui détermine si le taxon doit être enregistré ou juste vérifié.
    """
    try:
        newTaxon = request.get_json()  # objet contenant les métadonnées du taxon
        save = newTaxon.get(
            "save", False
        )  # Récupération du paramètre 'save', défini à False par défaut

        # Vérification de l'existence d'un taxon similaire dans la base de données
        existing_taxon = (
            db.session.query(Taxref)
            .filter(
                # avec une Convertion en minuscule uniquement de certains attributs pour une comparaison plus large
                db.func.lower(Taxref.lb_nom) == newTaxon.get("lb_nom").lower(),
                db.func.lower(Taxref.lb_auteur) == newTaxon.get("lb_auteur").lower(),
                db.func.lower(Taxref.nom_complet) == newTaxon.get("nom_complet").lower(),
                db.func.lower(Taxref.nom_valide) == newTaxon.get("nom_valide").lower(),
                db.func.lower(Taxref.nom_vern) == newTaxon.get("nom_vern").lower(),
                db.func.lower(Taxref.nom_vern_eng) == newTaxon.get("nom_vern_eng").lower(),
                db.func.lower(Taxref.url) == newTaxon.get("url").lower(),
                Taxref.regne == newTaxon.get("regne"),
                Taxref.phylum == newTaxon.get("phylum"),
                Taxref.classe == newTaxon.get("classe"),
                Taxref.ordre == newTaxon.get("ordre"),
                Taxref.famille == newTaxon.get("famille"),
                Taxref.sous_famille == newTaxon.get("sous_famille"),
                Taxref.tribu == newTaxon.get("tribu"),
                Taxref.id_statut == newTaxon.get("id_statut"),
                Taxref.id_habitat == newTaxon.get("id_habitat"),
                Taxref.id_rang == newTaxon.get("id_rang"),
                Taxref.group1_inpn == newTaxon.get("group1_inpn"),
                Taxref.group2_inpn == newTaxon.get("group2_inpn"),
            )
            .first()
        )

        if existing_taxon:
            return (
                jsonify(
                    {
                        "error": "Doublon en bdd",
                        "message": "Le taxon existe déjà dans la base de données.",
                    }
                ),
                409,
            )

        # Calcul de la prochaine valeur négative pour cd_nom
        next_cd_nom = db.session.query(
            db.func.coalesce(db.func.min(Taxref.cd_nom), 0) - 1
        ).scalar()

        # Création du nouvel enregistrement, avec une instertion dans les tables "taxref", "cor_nom_liste" et "bib_noms"
        add_Taxref = Taxref(
            cd_nom=next_cd_nom,
            cd_ref=next_cd_nom,
            lb_nom=newTaxon.get("lb_nom"),
            lb_auteur=newTaxon.get("lb_auteur"),
            nom_complet=newTaxon.get("nom_complet"),
            nom_valide=newTaxon.get("nom_valide"),
            nom_vern=newTaxon.get("nom_vern"),
            nom_vern_eng=newTaxon.get("nom_vern_eng"),
            url=newTaxon.get("url"),
            regne=newTaxon.get("regne"),
            phylum=newTaxon.get("phylum"),
            classe=newTaxon.get("classe"),
            ordre=newTaxon.get("ordre"),
            famille=newTaxon.get("famille"),
            sous_famille=newTaxon.get("sous_famille"),
            tribu=newTaxon.get("tribu"),
            id_statut=newTaxon.get("id_statut"),
            id_habitat=newTaxon.get("id_habitat"),
            id_rang=newTaxon.get("id_rang"),
            group1_inpn=newTaxon.get("group1_inpn"),
            group2_inpn=newTaxon.get("group2_inpn"),
        )
        add_CorNomListe_100 = CorNomListe(
            id_liste=100,
            id_nom=next_cd_nom,
        )
        add_CorNomListe_101 = CorNomListe(
            id_liste=101,
            id_nom=next_cd_nom,
        )
        add_BibNoms = BibNoms(
            cd_nom=next_cd_nom,
            cd_ref=next_cd_nom,
            nom_francais=newTaxon.get("nom_vern"),
        )

        # Si le paramètre "save" est à False,
        # le taxon n'est pas enregistré dans la base de données, même si l'insertion est possible.
        # Le système retourne alors un message indiquant que le taxon est valid
        # et peut être ajouté après vérification des doublons dans le fichier.

        # REMARQUE : cette fonctionnalité est utilisée pour l'insertion multiple de taxons.
        # Elle permet de vérifier que l'ensemble des taxons peut être inséré sans erreur (pas d'erreur SQL et pas de doublons
        # dans la base de données ni dans le fichier) avant de procéder à l'insertion.
        # Cela garantit que tous les taxons sont ajoutés en une seule opération ou aucun,
        # assurant ainsi une gestion plus cohérente et sécurisée de l'insertion multiple.
        if not save:
            return (
                jsonify(
                    {
                        "error": "correct",
                        "message": "Aucune erreur détectée. Le taxon est valide et peut être ajouté après vérification des doublons dans le fichier.",
                    }
                ),
                200,
            )

        # Si aucune erreur n'est rencontrée ET is save, insertion du taxon dans les différentes tables ...
        db.session.add(add_Taxref)
        db.session.add(add_CorNomListe_100)
        db.session.add(add_CorNomListe_101)
        db.session.add(add_BibNoms)
        db.session.commit()
        # avec envoie d'un message de succès une fois l'insertion effectuée
        return jsonify({"message": "Taxon ajouté avec succès !"}), 201

    # En cas d'erreur, capture de l'exception et retour d'un message d'erreur détaillé
    except Exception as e:
        return (
            jsonify(
                {
                    "error": "Autre erreur (le plus souvent une erreur de syntaxe, l'oubli d'un attribut, etc.)",
                    "message": str(e),
                }
            ),
            500,
        )


@adresses.route("/idNomStatuts", methods=["GET"])
@json_resp
def get_id_nom_statuts():
    """
    Retourne un dictionnaire contenant la liste des id des statuts et leur nom associé,
    trié par ordre alphabétique sur leurs noms.
    """
    subquery = (
        db.session.query(BibTaxrefStatus.id_statut, BibTaxrefStatus.nom_statut).distinct(
            BibTaxrefStatus.id_statut
        )
    ).subquery()
    data = db.session.query(subquery).order_by(subquery.c.nom_statut.asc()).all()
    return [{"id_statut": id_statut, "nom_statut": nom_statut} for id_statut, nom_statut in data]


@adresses.route("/idNomHabitats", methods=["GET"])
@json_resp
def get_id_nom_habitats():
    """
    Retourne un dictionnaire contenant la liste des id des habitats et leur nom associé,
    trié par ordre alphabétique sur leurs noms.
    """
    subquery = (
        db.session.query(BibTaxrefHabitats.id_habitat, BibTaxrefHabitats.nom_habitat).distinct(
            BibTaxrefHabitats.id_habitat
        )
    ).subquery()
    data = db.session.query(subquery).order_by(subquery.c.nom_habitat.asc()).all()
    return [
        {"id_habitat": id_habitat, "nom_habitat": nom_habitat} for id_habitat, nom_habitat in data
    ]


@adresses.route("/idNomRangs", methods=["GET"])
@json_resp
def get_id_nom_rangs():
    """
    Retourne un dictionnaire contenant la liste des id des rangs et leur nom associé,
    trié par ordre alphabétique sur leurs noms.
    """
    subquery = (
        db.session.query(BibTaxrefRangs.id_rang, BibTaxrefRangs.nom_rang).distinct(
            BibTaxrefRangs.id_rang
        )
    ).subquery()
    data = db.session.query(subquery).order_by(subquery.c.nom_rang.asc()).all()
    return [{"id_rang": id_rang, "nom_rang": nom_rang} for id_rang, nom_rang in data]


@adresses.route("/groupe1_inpn", methods=["GET"])
@json_resp
def get_group1_inpn_taxref():
    """
    Retourne la liste des groupes 1 inpn
    """
    data = (
        db.session.query(Taxref.group1_inpn)
        .distinct(Taxref.group1_inpn)
        .filter(Taxref.group1_inpn != None)
    ).all()
    return ["Non renseigné"] + [
        d[0] for d in data
    ]  # Placement du choix "Non renseigné" en tête de liste


@adresses.route("/groupe2_inpn", methods=["GET"])
@json_resp
def get_group2_inpn_taxref():
    """
    Retourne la liste des groupes 2 inpn
    """
    data = (
        db.session.query(Taxref.group2_inpn)
        .distinct(Taxref.group2_inpn)
        .filter(Taxref.group2_inpn != None)
    ).all()
    return ["Non renseigné"] + [
        d[0] for d in data
    ]  # Placement du choix "Non renseigné" en tête de liste
