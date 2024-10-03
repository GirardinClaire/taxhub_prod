// Service pour gérer les opérations liées aux taxons
app.service('TaxonService', ['$http', 'backendCfg', function($http, backendCfg) {

    // Récupère les statuts des noms de taxons
    this.getIdNomStatuts = function() {
        return $http.get(backendCfg.api_url + 'taxref/idNomStatuts') // Effectue une requête GET pour ajouter le taxon
            .then(response => response.data); // Retourne les données de la réponse
    };

    // Récupère les habitats des noms de taxons
    this.getIdNomHabitats = function() {
        return $http.get(backendCfg.api_url + 'taxref/idNomHabitats')
            .then(response => response.data);
    };

    // Récupère les rangs des noms de taxons
    this.getIdNomRangs = function() {
        return $http.get(backendCfg.api_url + 'taxref/idNomRangs')
            .then(response => response.data);
    };

    // Récupère le groupe 1 INPN
    this.getGroup1Inpn = function() {
        return $http.get(backendCfg.api_url + 'taxref/groupe1_inpn')
            .then(response => response.data);
    };

    // Récupère le groupe 2 INPN
    this.getGroup2Inpn = function() {
        return $http.get(backendCfg.api_url + 'taxref/groupe2_inpn')
            .then(response => response.data);
    };

    // Ajoute un nouveau taxon
    this.addTaxon = function(newTaxon, save) {
        newTaxon.save = save;  // Ajout du paramètre 'save' à l'objet 'newTaxon' pour gérer l'ajout multiple
        return $http.post(backendCfg.api_url + 'taxref/addTaxon', newTaxon) // Effectue une requête POST pour ajouter le taxon
            .then(response => response.data); // Retourne les données de la réponse
    };

}]);
