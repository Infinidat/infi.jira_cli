#! /bin/bash 

. /opt/tech-writing/rc.sh
verify_prerequisites

if [ "$1" = "" ] || [ "$2" = "" ] ; then
  echo "Usage: $0 {parent-version} {new-version} [ {users...} ]"
  exit -1
fi

SPACE=TWDRAFTS

PARENT_VERSION="$1"; shift
NEW_VERSION="$1"; shift

# Find parent version 
PARENT_VERSION_ID=$(wiki-find-scroll-version.sh "$PARENT_VERSION")
if [ "$PARENT_VERSION_ID" = "" ] ; then
  echo >&2 "Parent-version '$PARENT_VERSION' does not exist"
  exit -1
fi

NEW_VERSION_ID=$(wiki-find-scroll-version.sh "$NEW_VERSION")
if [ "$NEW_VERSION_ID" != "" ] ; then
  echo >&2 "New-version '$NEW_VERSION' already exists"
  exit -1
fi

# Create new version under parent
TASK=$(wiki POST "/rest/scroll-versions/1.0/versions/$SPACE"  '{ "name": "'$NEW_VERSION'", "precedingVersionId": "'$PARENT_VERSION_ID'", "runtimeAccessible": true }')
#echo >&2 $TASK
TASK_ID=$(echo $TASK | jq -r '.id')
while [ $(wiki GET "/rest/scroll-versions/1.0/async-tasks/$TASK_ID" |  jq -r '.finished') != "true" ] ; do
  echo >&2 -n "."
  sleep 1
done

NEW_VERSION_ID=$(wiki-find-scroll-version.sh "$NEW_VERSION")
#echo >&2 "NEW_VERSION_ID: $NEW_VERSION_ID"

RST=$(wiki GET /rest/scroll-versions/1.0/versions/$SPACE/restrictions  | jq ' 
  { "space": .space, 
    "versions": (  
        [ .versions[] | select (.versionId != "'$NEW_VERSION_ID'") ] + 
        [ { "versionId": "'$NEW_VERSION_ID'", 
            "editRestrictionGroups": [], 
            "editRestrictionUsers": [] 
          } 
        ] 
    ) 
  }')
#echo >&2 "New Restrictions: $RST"

TASK=$(wiki POST /rest/scroll-versions/1.0/versions/$SPACE/restrictions "$RST")
#echo >&2 $TASK
TASK_ID=$(echo $TASK | jq -r '.id')
while [ $(wiki GET "/rest/scroll-versions/1.0/async-tasks/$TASK_ID" |  jq -r '.finished') != "true" ] ; do
  echo >&2 -n "."
  sleep 1
done
echo >&2 ""

echo $NEW_VERSION_ID
