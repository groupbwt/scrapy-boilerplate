#!/bin/bash
set -eu
cd /var/app/typescript/src
npm install
npm run fbuild
pm2 status
# uncomment following line if pm2.config.js file existing in typescript/src dir and contain instructions
# to run worker processes. Or replace with required bash terminal instructions
#pm2 start pm2.config.js
node
