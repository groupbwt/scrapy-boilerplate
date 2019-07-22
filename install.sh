#!/bin/bash

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
pushd $DIR > /dev/null

read -p "Enter project name (snake_cased): " project_name

echo "Updating project name"
sed -ie "s/YOUR_PROJECT_NAME/$project_name/g" src/settings.py

read -p "Create new git repo? "
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing .git folder"
    rm -rf .git
    git init
fi

echo "Creating .env file"
cp -i src/.env.example src/.env

read -p "Clear README? "
if [[ $REPLY =~ ^[Yy]$ ]]; then
    dirname=${PWD##*/}
    echo -e "# $dirname\n" > README.md
    echo "Cleared README"
fi

echo "Setup finished, your project is ready!"
rm -f install.sh
popd > /dev/null
