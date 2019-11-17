
##### WARNING
This tool doesn't work as-is anymore. Glassdoor have recently changed their API to disallow anonymous searches, and introduce a strange credits system of earning the ability to search by contributing reviews. Pull requests are welcome.
## Glassdoor Scraper

Given a search keyword and a location (or multiple), scrapes glassdoor for listings

Handles pagination and rate limiting; does some hacks to try bypass the builtin query size limit. Retrieves and scrapes each listing's individual details page to get some additional information beyond what's presented in the search directly (namely, salary and full description text).

### Installation
* Install [nix](https://nixos.org/nix/) (a package manager that runs in parallel to your system package manager; works on linux and mac)
* In the repository root, run `nix-shell .`

### Usage
Currently, there's no CLI; run `nix-shell`, then import glassdoor in a REPL, and call `glassdoor.Search().run()`
