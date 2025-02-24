#!/bin/bash 
set -x

. /opt/tech-writing/rc.sh
verify_prerequisites

SPACE=TWDRAFTS

if [ "$1" = "" ] || [ "$2" = "" ] || [ $3 = "" ] || [ "$4" == "" ] ; then
	echo "Usage: $0 {new-page-title} {parent-page-title} {version} {XML-content}"
	exit -1
fi

NEW_TITLE="$1"
PARENT_TITLE="$2"
VERSION="$3"
CONTENT="$4"

# Find Scroll ID for the version
JSON=$(wiki GET "/rest/scroll-versions/1.0/versions/$SPACE")
VERSION_ID=$(jq -r '.[] | select(.name == "'$VERSION'") | .id' <<< $JSON)

# Find ID of parent page
CQL=$(echo 'space="'$SPACE'" and title="'$PARENT_TITLE'"' | jq -R -r @uri)
JSON=$(wiki GET "/rest/api/content/search?cql=$CQL")
PARENT_PAGE_ID=$(jq -r ".results[] | .id" <<< $JSON)

# Find ID of master/public page (if it exists)
CQL=$(echo 'space="'$SPACE'" and title="'$NEW_TITLE'"' | jq -R -r @uri)
JSON=$(wiki GET "/rest/api/content/search?cql=$CQL" )
MASTER_CONFL_ID=$(jq -r ".results[] | .id" <<< $JSON)

if [ "$MASTER_CONFL_ID" = "" ] ; then
	# Create empty page in master/public view, and store the new page ID
	JSON=$(echo '{"type":"page","title":"'$NEW_TITLE'","space":{"key":"'$SPACE'"},"ancestors":[{"id":'$PARENT_PAGE_ID'}],"body":{"storage":{"value":"","representation":"storage"}}}' | wiki POST "/rest/api/content/" "@-")
	MASTER_CONFL_ID=$(jq -r '.id' <<< $JSON)
fi

# Get the Scroll page ID for the master new page
JSON=$(wiki GET "/rest/scroll-versions/1.0/page/$SPACE/$MASTER_CONFL_ID")
MASTER_SCROL_ID=$(jq -r '.scrollPageId' <<< $JSON)


# Find versioned page
JSON=$(wiki GET "/rest/scroll-versions/1.0/page/$SPACE/$MASTER_SCROL_ID/$VERSION_ID")
VERSION_CONFL_ID=$(jq -r '.confluencePage.id' <<< $JSON)
VERSION_LATEST_ID=$(jq -r '.targetVersion.id' <<< $JSON)

if [ "$VERSION_CONFL_ID" = "" ] || [ "$VERSION_LATEST_ID" != "$VERSION_ID" ]; then
	# Create page in requested version
	JSON=$(wiki POST "/rest/scroll-versions/1.0/page/$SPACE/$MASTER_SCROL_ID/convertToVersioned?versionId=$VERSION_ID")
	VERSION_CONFL_ID=$( jq -r '.confluencePage.id' <<< $JSON)
fi

# Get internal title of the versioned page, and it's confluence version 
JSON=$(wiki GET "/rest/api/content/$VERSION_CONFL_ID")
VERSION_TITLE=$(jq -r '.title' <<< $JSON)
PAGEVER=$(wiki GET "/rest/api/content/$VERSION_CONFL_ID?expand=version" |  jq -r '.version.number')
PAGEVER=$(($PAGEVER+1))

# Update the versioned page with the supplied content
echo '{"type":"page","title":"'$VERSION_TITLE'","space":{"key":"'$SPACE'"},"ancestors":[{"id":'$PARENT_PAGE_ID'}],"version":{"number":'$PAGEVER'},"body":{"storage":{"value":"'$CONTENT'","representation":"storage"}}}' | wiki PUT /rest/api/content/$VERSION_CONFL_ID '@-'

