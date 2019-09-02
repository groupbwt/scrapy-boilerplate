#!/bin/bash

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
pushd $DIR > /dev/null

read -p "Is this a new project install? [Y/n] "
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    project_name=""
    while [[ -z $project_name ]]; do
        read -p "Enter project name (snake_cased): " project_name
        if [[ -z $project_name ]]; then
            echo "Project name must not be empty!"
        fi
    done

    echo "Creating .env files"
    cp -i src/.env.example src/.env
    cp -i .docker_env.example .env

    echo "Updating project name"
    sed -i "s/YOUR_PROJECT_NAME/$project_name/g" src/settings.py
    sed -i "s/YOUR_PROJECT_NAME/$project_name/g" .env

    read -p "Create new git repo? [y/N] "
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing .git folder"
        rm -rf .git
        git init
    fi

    read -p "Delete README? [y/N] "
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -f README.md
        echo "Deleted README"
    fi
fi

echo "Installing pipenv dependencies"
pushd ./src > /dev/null
pipenv install --dev --pre
popd > /dev/null

read -p "Add pre-commit hooks? [y/N] "
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pushd ./src > /dev/null
    PYTHON=$(pipenv --py)
    popd > /dev/null
    $PYTHON -m pre_commit install
fi

echo "Setup finished, your project is ready!"
popd > /dev/null
