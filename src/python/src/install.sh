#!/bin/bash

DIR="$( cd "$(dirname "$0")" ; pwd -P )"
pushd $DIR > /dev/null

FIRST_TIME=1
read -p "Is this a new project install? [Y/n] "
if [[ $REPLY =~ ^[Nn]$ ]]; then
    FIRST_TIME=0
fi

if [[ $FIRST_TIME == 1 ]]; then
    project_name=""
    while [[ -z $project_name ]]; do
        read -p "Enter project name (snake_cased): " project_name
        if [[ -z $project_name ]]; then
            echo "Project name must not be empty!"
        fi
    done
fi

echo "Creating .env files"
cp -i src/.env.example src/.env

if [[ $FIRST_TIME == 1 ]]; then
    echo "Updating project name"
    file_names=("src/settings.py" ".env" "pyproject.toml")
    for file_name in "${file_names[@]}"; do
        sed -i "s/YOUR_PROJECT_NAME/$project_name/g" "$file_name"
    done

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

echo "Installing poetry dependencies"
poetry install

read -p "Add pre-commit hooks? [y/N] "
if [[ $REPLY =~ ^[Yy]$ ]]; then
    poetry run python -m pre_commit install
fi

echo "Setup finished, your project is ready!"
popd > /dev/null
