# mcp-project-navigator

Serveur MCP de navigation et d'exploration de projets locaux.
L'objectif est de fournir a un LLM un ensemble d'outils précis pour
contextualiser un projet sur le plan de sa structure, de son contenu
et de ses fichiers sources, sans intervention manuelle du développeur.

Les projets sont enregistrés dans un fichier de configuration local
`paths.json` qui associe un identifiant court a un chemin absolu sur
le disque. Tous les outils opèrent a partir de cet identifiant.


## Outils disponibles

### list_projects

Liste tous les projets enregistrés dans la configuration.
Retourne les identifiants sous forme de liste et le nombre total
de projets indexés. Un flag optionnel permet d'inclure les chemins
associés a chaque identifiant.

### get_project_tree

Construit et retourne l'arborescence d'un projet enregistré.

Paramètres de filtrage disponibles :

- Profondeur maximale d'exploration (max_depth)
- Inclusion ou exclusion des fichiers et dossiers cachés (include_hidden)
- Patterns glob d'inclusion et d'exclusion (include, exclude)
- Fichier de patterns de type gitignore (exclude_from, par defaut `.gitignore`)

Les dossiers qui n'ont pas été explorés (profondeur atteinte, exclusion,
masquage) sont représentés dans l'arbre avec un statut explicite plutot
que d'être silencieusement omis. L'arbre peut etre retourné sous forme
d'objet JSON imbriqué ou de chaine de caractères avec branchages classiques.
La réponse inclut des statistiques agrégées (nombre de fichiers, taille
totale, répartition par extension, profondeur réelle atteinte) ainsi que
les avertissements non fatals rencontrés lors de la construction.

### read_project_file

Lit un fichier d'un projet enregistré et en retourne le contenu.

Paramètres optionnels :

- Plage de lignes a retourner (start_line, end_line), indicé à partir de 1
- Préfixage des lignes par leur numero (include_line_numbers)

La réponse inclut le langage détecté, le nombre total de lignes du
fichier et le nombre de lignes effectivement retournées.

### search_project_content

Recherche un terme ou un pattern dans les fichiers d'un projet,
a la manière de grep -rn.

Paramètres de recherche :

- Terme litteral ou expression regulière (pattern, use_regex)
- Correspondance insensible a la casse (ignore_case, actif par defaut)
- Nombre de lignes de contexte autour de chaque occurrence (context_lines)
- Filtres de fichiers identiques a get_project_tree (include, exclude,
  exclude_from, include_hidden)
- Limites de collecte pour maitriser la taille des réponses
  (max_matches_per_file, max_files)

Les occurrences adjacentes ou dont les fenêtres de contexte se chevauchent sont fusionnées en un seul bloc, conformément au comportement de grep -C.
Chaque ligne d'un bloc est typée : occurrence réelle ou ligne de contexte.
Les fichiers binaires sont ignorés silencieusement. Les fichiers non
décodables en UTF-8 sont signalés dans les avertissements de la réponse.
La réponse inclut des statistiques globales (fichiers examinés, fichiers
avec occurrences, total des occurrences, troncature éventuelle).


## Configuration

Les projets sont enregistrés manuellement dans le fichier suivant :

    ~/.config/scripts/mcp-project/paths.json

Format attendu :

    {
        "mon-projet": "/chemin/absolu/vers/mon-projet",
        "autre-projet": "/chemin/absolu/vers/autre-projet"
    }

Le fichier est crée automatiquement au premier démarrage du serveur.