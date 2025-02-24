#! /bin/bash

. /opt/tech-writing/rc.sh
verify_prerequisites

VERSION_ID=$(wiki GET "/rest/scroll-versions/1.0/versions/TWDRAFTS" | jq -r '.[] | select(.name == "PUBLISHED") | .id')

Q='/rest/api/space/TWDRAFTS/content/page?limit=100&start=0'
while [ "$Q" != "" ] ; do
  echo $Q
  P=$(wiki GET "$Q")
  IDS=$(echo $P | jq -r '.results[] | .id' )
  echo $IDS
  for ID in $IDS ; do
    echo $ID
    SC=$(wiki GET "/rest/scroll-versions/1.0/page/TWDRAFTS/$ID" | jq -r '.scrollPageId')
    wiki POST "/rest/scroll-versions/1.0/page/TWDRAFTS/$SC/convertToVersioned?versionId=$VERSION_ID"
  done
  Q=$(echo $P | jq -r '._links.next')
done

