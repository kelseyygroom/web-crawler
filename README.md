# Web Crawler

## Overview

This project is an implementation of a web crawler. The web crawler crawls all ics.uci.edu domains with "useful" information (i.e. ignoring site with low information value). It begins with a few ics.uci.edu starting urls, checks the HTTP response of each url as it is accessed, checks the validity of the url (in terms of staying within the ics.uci.edu domain), extracts all links from valid urls and adds them to the queue of links to visit. This project uses a spacetime crawler cache server to receive requests and avoid overloading ICS servers.

## Crawler Flow

The crawler receives a cache host and port from the spacetime servers and instantiates the config. It launches a crawler which creates a Frontier and Worker.

When the crawler is started, workers are created that pick up an undownloaded link from the frontier, download it from the cache server, and pass the response to the scraper function. The links that are received by the scraper is added to the list of undownloaded links in the frontier and the url that was downloaded is marked as complete. The cycle continues until there are no more urls to be downloaded in the frontier.
