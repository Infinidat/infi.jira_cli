#! /bin/bash 

. /opt/tech-writing/rc.sh
verify_prerequisites

if [ "$1" = "" ] ; then
  echo "Usage: $0 {version}"
  exit -1
fi

SPACE=TWDRAFTS

VERSION="$1"; shift

# Find version 
VERSION_ID=$(wiki GET "/rest/scroll-versions/1.0/versions/$SPACE" | jq -r '.[] | select(.name == "'$VERSION'") | .id')
echo "$VERSION_ID"
