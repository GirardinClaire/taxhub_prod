app.controller('addTaxonCtrl', ['$scope', 'TaxonService', 'loginSrv', function($scope, TaxonService, loginSrv) {

    var ctrl = this;

    ctrl.route = 'addTaxon';
    ctrl.viewMode = 'unique'; // Par défaut, l'affichage sera sur l'ajout unique

    ctrl.csvFile = null,
    ctrl.csvData = [];

    // Vérification du rôle de l'utilisateur : détermine si l'utilisateur est administrateur afin d'adapter le contenu de la page
    ctrl.isAdmin = loginSrv.getCurrentUserRights().admin;

    // Chargement des données au démarrage avec Promise.all
    Promise.all([
        TaxonService.getIdNomStatuts(),
        TaxonService.getIdNomHabitats(),
        TaxonService.getIdNomRangs(),
        TaxonService.getGroup1Inpn(),
        TaxonService.getGroup2Inpn()
    ]).then(([listStatuts, listHabitats, listRangs, listGroup1Inpn, listGroup2Inpn]) => {
        ctrl.statuts = listStatuts;
        ctrl.habitats = listHabitats;
        ctrl.rangs = listRangs;
        ctrl.group1Inpn = listGroup1Inpn;
        ctrl.group2Inpn = listGroup2Inpn;

        // Sauvegarde des valeurs par défaut dans une variable
        ctrl.defaultTaxon = {
            lb_nom: '',
            lb_auteur: '',
            nom_complet: '',
            nom_valide: '',
            nom_vern: '',
            nom_vern_eng: '',
            url: '',
            statut: ctrl.statuts.find(s => s.nom_statut === 'Non précisé'),
            id_statut: ctrl.statuts.find(s => s.nom_statut === 'Non précisé').id_statut,
            habitat: ctrl.habitats.find(h => h.nom_habitat === 'Non renseigné'),
            id_habitat: ctrl.habitats.find(h => h.nom_habitat === 'Non renseigné').id_habitat,
            id_rang: '',
            group1_inpn: '',
            group2_inpn: '',
        };

        // Initialisation de newTaxon avec les valeurs par défaut
        ctrl.resetForm();

        // Application des changements dans le $scope
        $scope.$apply();

        }).catch(error => {
            console.error("Erreur lors du chargement des données:", error);
        });



    //--------------------- Fonctions utiles ------------------------------------

    // Mise en place de watchers pour lb_nom et lb_auteur afin de compléter automatiquement le champ nom_complet
    $scope.$watchGroup(['ctrl.newTaxon.lb_nom', 'ctrl.newTaxon.lb_auteur'], function(newValues) {
        var lb_nom = newValues[0] || '';
        var lb_auteur = newValues[1] || '';
        if (ctrl.newTaxon) {
            ctrl.newTaxon.nom_complet = lb_nom + ' ' + lb_auteur;
        }
    });

    // Réinitialisation des champs du formulaire
    ctrl.resetForm = function() {
        ctrl.newTaxon = angular.copy(ctrl.defaultTaxon);
        $scope.$broadcast('resetTaxHierarchy'); // Appel de resetTaxHierarchy (Directive) pour réinitialiser les saisies des rangs taxonomiques
    };

    // Fonction appelée lorsqu'un fichier est sélectionné
    ctrl.uploadCSV = function(file) {
        ctrl.csvFile = file;
    };

    // Fonction pour retirer le fichier CSV sélectionné
    ctrl.removeCSV = function() {
        ctrl.csvFile = null;
    };

    // Insertion d'un nouveau taxon en Bdd
    ctrl.addTaxon = function(newTaxon, save) {
        newTaxon.nom_complet = newTaxon.lb_nom + ' ' + newTaxon.lb_auteur;
        // Retourne une promesse pour gérer l'asynchronisme
        return TaxonService.addTaxon(newTaxon, save)
            .then(response => {
                return response; // Réussite, on retourne la réponse
            })
            .catch(error => {
                throw error; // Sinon, on relance l'erreur pour la gérer avec 'await'
            });
    };
    


    //--------------------- Ajout de nouveau(x) taxon(s) ------------------------------------

    // Ajout unique
    ctrl.addTaxonForm = function(newTaxon) {
        // Vérification des champs obligatoires
        if (!newTaxon.lb_nom || !newTaxon.rang || newTaxon.group1_inpn === '' || newTaxon.group2_inpn === '') {
            alert("Veuillez remplir tous les champs obligatoires.\n A savoir : 'Nom du taxon', 'Rang', 'Groupe INPN 1' et 'Groupe INPN 2'");
            return;
        }

        // Convertions respectives de statut, habitat et rang en id_statut, id_habitat et id_rang
        newTaxon.id_statut = newTaxon.statut.id_statut;
        newTaxon.id_habitat = newTaxon.habitat.id_habitat;
        newTaxon.id_rang = newTaxon.rang.id_rang.trim(); // ATTENTION : Utilisation de trim() pour retirer les espaces
                                                        // afin d'assurer la cohérence du stockage sur 2 caractères,
                                                        // comme défini dans la table taxref.
                                                        // Note : Le caractère récupéré de bib_taxref_rangs est sur 4 caractères,
                                                        // par ex. 'TR  ', tandis que dans taxref, il est stocké sous la forme 'TR'.
        
        // Récupération des rangs taxonomiques choisis
        newTaxon.regne = newTaxon.rangTaxonomique?.regne ?? '';
        newTaxon.phylum = newTaxon.rangTaxonomique?.phylum ?? '';
        newTaxon.classe = newTaxon.rangTaxonomique?.classe ?? '';
        newTaxon.ordre = newTaxon.rangTaxonomique?.ordre ?? '';
        newTaxon.famille = newTaxon.rangTaxonomique?.famille ?? '';
        newTaxon.sous_famille = newTaxon.rangTaxonomique?.sous_famille ?? '';
        newTaxon.tribu = newTaxon.rangTaxonomique?.tribu ?? '';

        // Nettoyage des propriétés inutilisées
        delete newTaxon.statut;
        delete newTaxon.habitat;
        delete newTaxon.rang;
        delete newTaxon.rangTaxonomique;

        // Insertion du taxon en bdd avec message de réussite ou d'erreur
        ctrl.addTaxon(newTaxon, true) // Paramètre save = true pour permettre une insertion immédiate en l'absence d'erreurs
            .then(response => {
                alert(response.message);
            })
            .catch(error => {
                alert("ECHEC DE L'AJOUT.\n Erreur : "+error.data.message);
            });
        
        ctrl.resetForm(); // Réinitialisation du formulaire après l'ajout
    };


    // Ajouts multiples
    ctrl.addTaxonsCSV = async function() {
        if (ctrl.csvFile) {
            // Parsing du fichier csv déposé
            Papa.parse(ctrl.csvFile, {
                complete: async function(results) {
                    $scope.$apply(async function() {
                        ctrl.csvData = results.data;
                        let i = 0;
                        let j = 0;
                        let k = 0;
                        ctrl.errors = []; // Réinitialisation des erreurs
                        let seenTaxons = new Set();  // Définition d'un ensemble pour stocker les taxons déjà traités

                        // Double vérification en BDD : insertion possible + doublon dans la bdd
                        for (const taxon of ctrl.csvData) {
                            i ++;
                            // Boucle asynchrone pour attendre chaque vérification
                            try {
                                await ctrl.addTaxon(taxon, false); // Paramètre save = false pour ne pas enregistrer de taxon pendant cette phase de vérification
                            } catch (error) {
                                if (error.data.error != "correct") {
                                    ctrl.errors.push({ligne: i, type: error.data.error, msg: error.data.message});
                                }
                            }
                        }

                        // Vérification des doublons au sein même du fichier
                        for (const taxon of ctrl.csvData) {
                            j ++;
                            try {
                                // Création d'une clé unique en concaténant les valeurs à vérifier (avec certains champs mis en minuscule pour une vérification plus large)
                                let taxonKey = (taxon.lb_nom.toLowerCase() + taxon.lb_auteur.toLowerCase() + 
                                                taxon.nom_complet.toLowerCase() + taxon.nom_valide.toLowerCase() +
                                                taxon.nom_vern.toLowerCase() + taxon.nom_vern_eng.toLowerCase() +
                                                taxon.url.toLowerCase() +
                                                taxon.regne + taxon.phylum +
                                                taxon.classe + taxon.ordre +
                                                taxon.famille + taxon.sous_famille +
                                                taxon.tribu +
                                                taxon.id_statut + taxon.id_habitat +
                                                taxon.id_rang +
                                                taxon.group1_inpn + taxon.group2_inpn);
                                if (seenTaxons.has(taxonKey)) {
                                    ctrl.errors.push({ligne: j, type: "Doublon interne", msg: "Taxon dupliqué au sein du fichier."});
                                } else {
                                    seenTaxons.add(taxonKey);  // Ajout de la clé au Set
                                }
                            } catch (error) {
                                alert("Erreur lors de la vérification des doublons au sein du fichier: " + error.message);
                            }
                        }

                        // Tri des erreurs par ordre croissant de ligne
                        ctrl.errors.sort((a, b) => a.ligne - b.ligne);

                        // SI 0 erreur : insertion de TOUS les taxons du fichier
                        if (ctrl.errors.length == 0) {
                            for (const taxon of ctrl.csvData) {
                                k ++;
                                // Boucle asynchrone pour attendre chaque ajout, et éviter des erreurs d'attibution de cd_nom notamment
                                try {
                                    await ctrl.addTaxon(taxon, true); // Cette fois ci, paramètre save = true pour permettre une insertion immédiate
                                } catch (error) {
                                    alert("ECHEC ANORMAL DE L'AJOUT de la ligne numéro " + k + ". \n Veuillez procéder à des vérifications à la main en base de données.");
                                }
                            }
                            alert('Tous les taxons (' + ctrl.csvData.length + ' taxons) du fichier csv "' + ctrl.csvFile.name + '" ont été ajoutés avec succès !');
                        } else { // SINON affichage des messages d'erreur
                            alert("ECHEC DE L'AJOUT DES TAXONS. Veuillez vérifier les erreurs affichées sur la page.");
                        }
                        
                        // Réinitialisation du fichier CSV en forçant Angular à détecter le changement
                        ctrl.csvFile = null;
                        $scope.$apply();
                    });
                },
                header: true
            });
        } else {
            // Cas de validation d'importation sans fichier sélectionné
            alert("Veuillez sélectionner un fichier CSV.");
        }
    };

}]);
