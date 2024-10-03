// Directive pour ajouter une hiérarchie taxonomique
// Inspirée de la directive 'searchHierarchie-directive.js'
app.directive('addHierarchieDir', ['$http', 'backendCfg', function ($http, backendCfg) {
  return {
      restrict: 'AE', // La directive peut être utilisée comme une balise ou un attribut
      templateUrl: 'static/app/components/directives/addHierarchie-template.html', // Template HTML associé à la directive
      scope: {
          taxHierarchieSelected: '=', // Liaison bidirectionnelle avec la hiérarchie taxonomique sélectionnée
          searchUrl: '@', // URL de recherche passée en tant qu'attribut
      },
      link: function($scope, $element, $attrs) {
          // Initialisation de la directive : écoute les changements dans 'taxHierarchieSelected'
          $scope.$watch('taxHierarchieSelected', function(newVal, oldVal) {
              // Vérifie si une hiérarchie taxonomique est sélectionnée
              if ($scope.taxHierarchieSelected) {
                  // Mise à jour des propriétés de la hiérarchie selon les niveaux taxonomiques
                  if ($scope.taxHierarchieSelected.regne)
                      $scope.regne = {'regne': $scope.taxHierarchieSelected.regne, 'nb_tx_kd': $scope.taxHierarchieSelected.nb_tx_kd };
                  else $scope.regne = undefined;

                  if ($scope.taxHierarchieSelected.phylum)
                      $scope.phylum = {'phylum': $scope.taxHierarchieSelected.phylum, 'nb_tx_ph': $scope.taxHierarchieSelected.nb_tx_ph };
                  else $scope.phylum = undefined;

                  if ($scope.taxHierarchieSelected.classe)
                      $scope.classe = {'classe': $scope.taxHierarchieSelected.classe, 'nb_tx_cl': $scope.taxHierarchieSelected.nb_tx_cl };
                  else $scope.classe = undefined;

                  if ($scope.taxHierarchieSelected.ordre)
                      $scope.ordre = {'ordre': $scope.taxHierarchieSelected.ordre, 'nb_tx_or': $scope.taxHierarchieSelected.nb_tx_or };
                  else $scope.ordre = undefined;

                  if ($scope.taxHierarchieSelected.famille)
                      $scope.famille = {'famille': $scope.taxHierarchieSelected.famille, 'nb_tx_fm': $scope.taxHierarchieSelected.nb_tx_fm };
                  else $scope.famille = undefined;

                  if ($scope.taxHierarchieSelected.sous_famille)
                      $scope.sous_famille = {'sous_famille': $scope.taxHierarchieSelected.sous_famille, 'nb_tx_sbfm': $scope.taxHierarchieSelected.nb_tx_sbfm };
                  else $scope.sous_famille = undefined;

                  if ($scope.taxHierarchieSelected.tribu)
                      $scope.tribu = {'tribu': $scope.taxHierarchieSelected.tribu, 'nb_tx_tr': $scope.taxHierarchieSelected.nb_tx_tr };
                  else $scope.tribu = undefined;
              }
          }, true); // L'écouteur est déclenché sur les changements profonds

          // Fonction appelée lors de la sélection d'un élément
          $scope.onSelect = function ($item, $model, $label) {
              // Stocke l'élément sélectionné et ses informations associées
              $scope.$item = $item;
              $scope.$model = $model;
              $scope.$label = $label;
              this.taxHierarchieSelected = $item; // Met à jour la hiérarchie sélectionnée
          };

          // Fonction pour obtenir la hiérarchie des taxons en fonction du rang
          $scope.getTaxonHierarchie = function(rang, val, model) {
              var queryparam = { params: { 'ilike': val.trim() } }; // Paramètre de requête pour la recherche
              if (model) {
                  // Ajout des paramètres basés sur le modèle et le rang
                  if ((model.regne) && (rang !== 'KD'))
                      queryparam.params.regne = model.regne.trim();

                  if ((model.phylum) && ((rang !== 'PH') && (rang !== 'KD')))
                      queryparam.params.phylum = model.phylum.trim();

                  if ((model.classe) && ((rang !== 'CL') && (rang !== 'PH') && (rang !== 'KD')))
                      queryparam.params.classe = model.classe.trim();

                  if ((model.ordre) && ((rang !== 'OR') && (rang !== 'CL') && (rang !== 'PH') && (rang !== 'KD')))
                      queryparam.params.ordre = model.ordre.trim();

                  if ((model.famille) && ((rang !== 'FM') && (rang !== 'OR') && (rang !== 'CL') && (rang !== 'PH') && (rang !== 'KD')))
                      queryparam.params.famille = model.famille.trim();

                  if ((model.sous_famille) && ((rang !== 'SBFM') && (rang !== 'FM') && (rang !== 'OR') && (rang !== 'CL') && (rang !== 'PH') && (rang !== 'KD')))
                      queryparam.params.sous_famille = model.sous_famille.trim();
              }
              // Envoi de la requête HTTP GET pour récupérer la hiérarchie des taxons
              return $http.get(backendCfg.api_url + this.searchUrl + rang, queryparam).then(function(response) {
                  return response.data; // Retourne les données de la réponse
              });
          };

          // Fonction pour vider la sélection des rangs taxonomiques
          $scope.refreshForm = function() {
              if ($scope.taxHierarchieSelected === undefined) {
                  alert("La hiérarchie taxonomique est déjà vide."); // Alerte si la hiérarchie est déjà vide
              } else {
                  $scope.resetTaxHierarchy(); // Réinitialise la hiérarchie taxonomique
              }
          };

          // Réinitialisation des propriétés de la hiérarchie taxonomique
          $scope.resetTaxHierarchy = function() {
              $scope.taxHierarchieSelected = undefined; // Réinitialise la sélection
              // Réinitialise tous les niveaux taxonomiques
              $scope.regne = undefined;
              $scope.phylum = undefined;
              $scope.classe = undefined;
              $scope.ordre = undefined;
              $scope.famille = undefined;
              $scope.sous_famille = undefined;
              $scope.tribu = undefined;
          };

          // Écoute l'événement de réinitialisation pour faire le lien entre le contrôleur et la directive
          $scope.$on('resetTaxHierarchy', function() {
              $scope.resetTaxHierarchy(); // Appelle la fonction de réinitialisation
          });

      }
  }
}]);
