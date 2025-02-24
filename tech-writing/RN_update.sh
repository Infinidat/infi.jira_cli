#! /bin/bash
set -e
set -x


. /opt/tech-writing/rc.sh
verify_prerequisites
VAR_MAXIMUM_ISSUES=300

function usage {
    cat << END
Usage: $0 {HPT|HPTVM} {Version} {Status}
Where: Version is the 3-digit release number, e.g. 6.0.10
       Status is DRAFT or GA
END
}



PRODUCT=$1; shift
case $PRODUCT in
    HPT|HPTVM)   ;;
    *) usage; exit -1;;
esac

VERSION=$1; shift
if [ "$VERSION" = "" ] ; then
    usage; exit -1;
fi
MAJOR=${VERSION/.*/}

STATUS=$1; shift
case $STATUS in
    GA)    echo;;
    DRAFT) echo;;
    *)     usage; exit -1;;
esac


SCROLL="Host-RNs"
SCROLL_ID=$(wiki-find-scroll-version.sh $SCROLL)
if [ "$SCROLL_ID" = "" ] ;then
    SCROLL_ID=$(wiki-create-scroll-version.sh "PUBLISHED" $SCROLL)
fi


case $PRODUCT in
    HPT) JIRAPROJ=HPT;;
    HPTVM) JIRAPROJ=HPTVM;;
    *) usage; exit -1;;
esac

ALLVERS="$(jira GET /rest/api/latest/project/$JIRAPROJ/versions | jq -r '.[]? | .name')"
A=$(echo $VERSION | awk -F. '{print $1}')
B=$(echo $VERSION | awk -F. '{print $2}')
C=$(echo $VERSION | awk -F. '{print $3}')
if [ -n "$ALLVERS" ] && [ $(echo " $ALLVERS " | grep -c "$A\.$B\.$C\.") -ne 0 ]  ; then
	VERCHK='(fixVersion ~ "'$VERSION'.*" or fixVersion = '$VERSION') '
else
	VERCHK='(fixVersion = '$VERSION') '
fi
for ((i=0;i<$A;i++)); do if [ $(echo " $ALLVERS " | grep -c "^$i\."      ) != 0 ] ; then VERCHK="$VERCHK and fixVersion !~ \"$i.*\" ";                                  fi; done
for ((i=0;i<$B;i++)); do if [ $(echo " $ALLVERS " | grep -c "^$A\.$i\."  ) != 0 ] ; then VERCHK="$VERCHK and fixVersion !~ \"$A.$i.*\" ";                               fi; done 
for ((i=0;i<$C;i++)); do if [ $(echo " $ALLVERS " | grep -c "^$A.$B.$i\.") != 0 ] ; then VERCHK="$VERCHK and fixVersion !~ \"$A.$B.$i.*\" and fixVersion != $A.$B.$i "; fi; done  


FIELD_RN_SEVERITY=customfield_15547
FIELD_RN_TITLE=customfield_12507
FIELD_RN_DESCR=customfield_12508

function jql_table {
    JQL=$(echo "$1 order by severity ASC, key ASC"  | jq -R -r @uri)
    RSLT="$(jira GET "/rest/api/latest/search?jql=$JQL")"
    RSLT=$(echo "$RSLT" | sed -r 's/\&/\&amp;/g' | sed -r 's/\*/\&#39;\*\&#39;/g' | sed -r 's/</\&lt;/g')

    echo "$RSLT" | jq -r '.issues[] | "<tr><td>" + .fields.'$FIELD_RN_SEVERITY'.value + "</td><td>" + .key + "</td><td>" + .fields.'$FIELD_RN_TITLE' + "</td><td>" + .fields.'$FIELD_RN_DESCR' + "</td></tr>"' 
}

function jql_list {
    JQL=$(echo "$1 order by severity ASC, key ASC"  | jq -R -r @uri)
    RSLT="$(jira GET "/rest/api/latest/search?jql=$JQL")"
    RSLT=$(echo "$RSLT" | sed -r 's/\&/\&amp;/g' | sed -r 's/\*/\&#39;\*\&#39;/g' | sed -r 's/</\&lt;/g')

    echo "$RSLT" | jq -r '.issues[] | "<li><span>" + .key + " &#160;" + .fields.'$FIELD_RN_TITLE' + "</span></li>" + (if .fields.'$FIELD_RN_DESCR' != null then "<ul><li><span>" + .fields.'$FIELD_RN_DESCR' + "</span></li></ul>" else "" end)'
}


PRED_VERSION="AND $VERCHK"
PRED_RN_TITLE="AND \"Release Notes Title\" is NOT EMPTY"
PRED_CANDIDATES="AND \"Candidate for release notes\" = Yes AND (\"Excluded from the Release Notes\" is EMPTY OR \"Excluded from the Release Notes\" = No)"
CANDID4RN='&quot;Candidate for release notes&quot;'
RN_TYPE='&quot;Release Notes Type&quot;'
EXCL_FROM_RN='&quot;Excluded from the Release Notes&quot;'

if [ "$PRODUCT" = "CSI" ] ; then PRED_CANDIDATES=""; fi

function whatnew      { jql_list  "\"Release Notes Type\" = WHATSNEW     AND project=$1 $PRED_VERSION $PRED_RN_TITLE $PRED_CANDIDATES"; }
function fixed        { jql_table "\"Release Notes Type\" = FIXED        AND project=$1 $PRED_VERSION $PRED_RN_TITLE $PRED_CANDIDATES"; }
function improvements { jql_list  "\"Release Notes Type\" = IMPROVEMENTS AND project=$1 $PRED_VERSION $PRED_RN_TITLE $PRED_CANDIDATES"; }
function changes      { jql_list  "\"Release Notes Type\" = CHANGES      AND project=$1 $PRED_VERSION $PRED_RN_TITLE $PRED_CANDIDATES"; }
function notes        { jql_list  "\"Release Notes Type\" = NOTES        AND project=$1 $PRED_VERSION $PRED_RN_TITLE $PRED_CANDIDATES"; }
function warnings     { jql_list  "\"Release Notes Type\" = WARNINGS     AND project=$1 $PRED_VERSION $PRED_RN_TITLE $PRED_CANDIDATES"; }
function known        { jql_table "project =$1 AND (status = Open) AND \"Candidate for release notes\" = Yes AND \"Release Notes Type\" = Known AND (type = Bug); }


function table {
	TABLETOP=
	HEADING="$1"
	DATA="$2"
	if [ ! -z "$DATA" ] ; then
	  echo "<h2>$HEADING</h2>"
	  echo '
        <table class="wrapped fixed-table"><colgroup><col style="width: 75.0px;" /><col style="width: 171.0px;" /><col style="width: 483.0px;" /><col style="width: 697.0px;" /></colgroup>
        <tbody>
        <tr>
        <th style="text-align: left;"><span class="jim-table-header-content">Severity</span></th>
        <th style="text-align: left;"><span class="jim-table-header-content">Key</span></th>
        <th style="text-align: left;"><span class="jim-table-header-content">Release Notes Title</span></th>
        <th style="text-align: left;"><span class="jim-table-header-content">Release Notes Description</span></th></tr>
        '
	  echo "$DATA"
	  echo '</tbody></table>'
    fi
}

function list {
	HEADING="$1"
	DATA="$2"
	if [ ! -z "$DATA" ] ; then
	  echo "<h2>$HEADING</h2><ul>"
	  echo "$DATA"
	  echo '</ul>'
	fi
}


case $PRODUCT in
    HPT)
        TITLE="$PRODUCT $VERSION Release Notes - Internal"
        MAJORPAGETITLE="Host PowerTools Release Notes"
        WHATSNEW="     $(list "What's New in HPT Release $VERSION" "$(whatnew HPT $VERSION)")"
        FIXED="        $(table "HPT $VERSION Fixed Issues" "$(fixed HPT $VERSION)")          "
        IMPROVEMENTS=" $(list "HPT $VERSION Improvements" "$(improvements HPT $VERSION)")    "
        CHANGES="      $(list "HPT $VERSION Changes" "$(changes HPT $VERSION)")              "
        NOTES="        $(list "HPT $VERSION Notes" "$(notes HPT $VERSION)")                  "
        WARNINGS="     $(list "HPT $VERSION Warnings" "$(warnings HPT $VERSION)")            "
        KNOWN="        $(table "HPT $VERSION Known Issues" "$(known HPT $VERSION)")          "
        UPGRADE=''
		;;
    HPTVM)
        TITLE="$PRODUCT $VERSION Release Notes - Internal"
        MAJORPAGETITLE="Host PowerTools for VMware Release Notes"
        WHATSNEW="     $(list "What's New in HPTVM Release $VERSION" "$(whatnew HPTVM $VERSION)")"
        FIXED="        $(table "HPTVM $VERSION Fixed Issues" "$(fixed HPTVM $VERSION)")          "
        IMPROVEMENTS=" $(list "HPTVM $VERSION Improvements" "$(improvements HPTVM $VERSION)")    "
        CHANGES="      $(list "HPTVM $VERSION Changes" "$(changes HPTVM $VERSION)")              "
        NOTES="        $(list "HPTVM $VERSION Notes" "$(notes HPTVM $VERSION)")                  "
        WARNINGS="     $(list "HPTVM $VERSION Warnings" "$(warnings HPTVM $VERSION)")            "
        KNOWN="        $(table "HPTVM $VERSION Known Issues" "$(known HPTVM $VERSION)")          "
        UPGRADE=''
        ;;
esac



echo "### Generating headers"
case $STATUS in
    DRAFT)
        HEADER='
            <p class="auto-cursor-target">Document status: <span style="color: rgb(255,0,0);"><strong>DRAFT</strong></span></p>
            <ac:structured-macro ac:name="warning" ac:schema-version="1" ac:macro-id="a6c3637d-6fe2-4e8e-bcd7-c880ca8f9926">
            <ac:rich-text-body><p>This page is auto-generated by RN_update.sh</p></ac:rich-text-body>
            </ac:structured-macro>
        '
        DATE='<span style="color: rgb(0,0,0);"><span style="color: rgb(255,0,0);"><strong>TBD</strong></span></span>'
        ;;
    GA)
        HEADER='
            <p class="auto-cursor-target">Document status: <span style="color: rgb(0,255,0);"><strong>GA</strong></span></p>
            <ac:structured-macro ac:name="warning" ac:schema-version="1" ac:macro-id="a6c3637d-6fe2-4e8e-bcd7-c880ca8f9926">
            <ac:rich-text-body><p>Do not modify this page!</p></ac:rich-text-body>
            </ac:structured-macro>
        '
        DATE=$(date +"%B %d, %Y")
        ;;
esac



REVIEWERS='
  <h2>Release Notes Teams</h2>
  <table class="wrapped relative-table" style="width: 39.7576%;">
    <colgroup>
	  <col style="width: 14.7345%;" />
	  <col style="width: 43.7865%;" />
	  <col style="width: 41.2844%;" />
	  <col style="width: 43.7865%;" />
	</colgroup>
  <tbody>
    <tr> <th>Group</th>        <th>HPT</th></tr>
    <tr> <td>Tech Writing</td> <td>Shira</td></tr>
    <tr> <td>Product</td>      <td>Yossi</td></tr>
    <tr> <td>RnD</td>          <td>Depending on ticket</td></tr>
    <tr> <td>QA</td>           <td>Moran</td></tr>
    <tr> <td>Support</td>      <td>Dor Vardi</td></tr>
    </tbody></table>
  '

function jira_query_macro {
  QUERY_HEADING="$1"
  QUERY_EXPLANATION="$2"
  QUERY_COLUMNS="$3"
  QUERY_JQL="$4"
  cat << EOF
    <h2>$QUERY_HEADING</h2>
    <p>$QUERY_EXPLANATION</p>
    <p><ac:structured-macro ac:name="jira" ac:schema-version="1" ac:macro-id="e5788f69-0052-4fa2-9da1-68c38452842c">
    <ac:parameter ac:name="server">Infinidat</ac:parameter>
    <ac:parameter ac:name="columns">$QUERY_COLUMNS</ac:parameter>
    <ac:parameter ac:name="maximumIssues">$VAR_MAXIMUM_ISSUES</ac:parameter>
    <ac:parameter ac:name="jqlQuery">$QUERY_JQL </ac:parameter>
    <ac:parameter ac:name="serverId">7d107fb2-c596-3580-b7d6-c7a7101df405</ac:parameter>
    </ac:structured-macro></p>
EOF
}


case $PRODUCT in
    HPT) ALLJIRAPROJ=HPT;;
    HPTVM) ALLJIRAPROJ=HPTVM;;
    *) usage; exit -1;;
esac


ALL_RN_TICKETS="$(jira_query_macro \
    'Release Notes tickets' \
    'These tickets will appear in the release notes.' \
    'key,Release Notes Type,Release Notes Title' \
	"project in ($ALLJIRAPROJ) and (labels=RN-$PRODUCT-$VERSION-known-issues OR ($VERCHK AND resolution = Fixed AND status != Rejected AND ((&quot;Candidate for release notes&quot; = Yes AND (&quot;Excluded from the Release Notes&quot; is EMPTY OR &quot;Excluded from the Release Notes&quot; = No)) OR &quot;Release Notes Title&quot; is not EMPTY))) " \
    )"

IBOX_TICKETS_BY_TEAM=""



CANDIDATE_KNOWN="$(jira_query_macro \
    'Candidates for known issues from RnD that require review' \
    'Marked as known issues but might have been fixed.' \
    'key,summary,type,status,resolution,assignee,reporter,created,updated,priority' \
    "project in ($ALLJIRAPROJ)
    AND (fixVersion > 7.2.40)
    AND \"Candidate for release notes\" = Yes
    AND \"Release Notes Type\" = Known
    AND (type = Bug)
    AND status != Rejected" \
    )"



CANDIDATE_FIXED="$(jira_query_macro \
    'Candidates for fixed issues from RnD that require review' \
    'These tickets are marked as candidates for release notes by RnD, but their Release Notes Title field is empty. The recommended action is to provide a Release Notes Title and set the Release Notes Type field to Fixed, or to set the Excluded from Release Notes field to Yes.' \
    'key,summary,type,created,updated,due,assignee,reporter,priority,status,resolution' \
	"project in ($ALLJIRAPROJ) and $VERCHK AND resolution = Fixed AND status != Rejected AND &quot;Candidate for release notes&quot; = Yes AND &quot;Release Notes Title&quot; is EMPTY AND (&quot;Excluded from the Release Notes&quot; is EMPTY OR &quot;Excluded from the Release Notes&quot; = No)" \
    )"

CANDIDATE_ZEN="$(jira_query_macro \
    'Fixed tickets linked to CS/ZEN tickets' \
    'These tickets are NOT marked as candidates for release notes by RnD, but they have links to customer tickets. Best practice is to either provide a Release Notes Title and set the Release Notes Type field to Fixed, or to set the Excluded from Release Notes field to Yes. ' \
    'key,summary,type,created,updated,due,assignee,reporter,priority,status,resolution' \
	"project in ($ALLJIRAPROJ) and $VERCHK AND resolution = Fixed AND status != Rejected AND ( &quot;Candidate for release notes&quot; is EMPTY OR &quot;Candidate for release notes&quot; = No) AND (&quot;Excluded from the Release Notes&quot; is EMPTY) AND ( issueFunction in linkedIssuesOf(&quot;project=CS&quot;) OR issueFunction in linkedIssuesOf(&quot;project=ZEN&quot;) )" \
    )"



cat <<END >page.data
$HEADER
<p class="auto-cursor-target"><br /></p>

<ac:structured-macro ac:name="excerpt" ac:schema-version="1" ac:macro-id="c9d80e64-a7e4-4487-a2c4-3bc66c8cc0a1">
  <ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter>
  <ac:rich-text-body>
    <h1>Release $VERSION</h1>
    <h2>Release Date</h2>
    <ul><li>$DATE</li></ul>
    $UPGRADE
    $WHATSNEW
    $IMPROVEMENTS
    $CHANGES
    $NOTES
    $WARNINGS
    $FIXED
    $KNOWN
  </ac:rich-text-body>
</ac:structured-macro>

<p><br/></p>
<p><br/></p>
<p><br/></p>
<hr/>
<hr/>
<hr/>

<ac:structured-macro ac:name="warning" ac:schema-version="1" ac:macro-id="a6c3637d-6fe2-4e8e-bcd7-c880ca8f9926">
  <ac:rich-text-body><p>The following will not appear in the Release Notes page.</p></ac:rich-text-body>
</ac:structured-macro>

<h1>Review Helper</h1>

$REVIEWERS
$ALL_RN_TICKETS
$IBOX_TICKETS_BY_TEAM
$CANDIDATE_KNOWN
$CANDIDATE_FIXED
$CANDIDATE_ZEN

END


CHECK=$(dos2unix page.data)
if [ $? != 0 ]; then
  echo "dos2unix did not execute properly."
  echo $CHECK
  exit -1
fi

CHECK=$( (echo "<A>"; cat  page.data | sed 's/ac://g'; echo "</A>") | xmllint - )
if [ $? != 0 ]; then
  echo "RN page cannot be updated."
  echo $CHECK
  exit -1
fi


sed -i 's/\"/\\\"/g' page.data

echo "TITLE :" $TITLE
echo "MAJORPAGETITLE :" $MAJORPAGETITLE
echo "SCROLL :" $SCROLL

PAGE=$(wiki-create-page-version.sh "$TITLE" "$MAJORPAGETITLE" "$SCROLL"  "$(cat page.data)" )
RNPAGEID=$(echo "$PAGE" | jq -r .id )
LABELED=$(wiki POST "/rest/api/content/$RNPAGEID/label" '[ { "prefix": "global", "name": "zendesk-skip-sync" }, { "prefix": "global", "name": "pdf-excluded" } ]' )

echo
echo
exit
