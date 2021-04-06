#!/bin/bash

# If NEW_VERSION environment variable is not set, prompt for new version number
# Version can be changed programatically with something like
# NEW_VERSION=1.2.3 ./change_version.sh

PACKAGE_NAME=thorlabs_apt_device

CURRENT_VERSION=$(grep -o -m 1 -E "[0-9]+\.[0-9]+\.[0-9]+" "setup.py")

if [[ "${CURRENT_VERSION}" == "" ]] ; then
  echo 'Unable to determine current version number of application. Check setup.py file
  and ensure version="x.y.z" ... is present, where x, y, and z are numbers.'
  exit 1
fi

echo "Detected version as ${CURRENT_VERSION}"

while ! [[ "${NEW_VERSION}" =~ [0-9]+\.[0-9]+\.[0-9]+ ]] ; do
    read -p "New version number in the form x.y.z [${CURRENT_VERSION}]: " NEW_VERSION
    if [[ "${NEW_VERSION}" == "" ]] ; then
      exit 0
    fi
done

echo "Changing version number to ${NEW_VERSION}"

# Update version number in package __init__.py
sed -i -e "s/__version__ = \"${CURRENT_VERSION}\"/__version__ = \"${NEW_VERSION}\"/" "${PACKAGE_NAME}/__init__.py"
# Update version number in setup.py for package
sed -i -e "s/version=\"${CURRENT_VERSION}\"/version=\"${NEW_VERSION}\"/" "setup.py"
# Update version number in conf.py for documentation
sed -i -e "s/release = '${CURRENT_VERSION}'/release = '${NEW_VERSION}'/" "doc/source/conf.py"
