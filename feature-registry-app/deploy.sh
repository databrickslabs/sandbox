echo_red() {
    echo "\033[1;31m$*\033[0m"
}

# Validate the current folder
[[ -d "./src" && -f "./src/app.yaml" ]] || { echo_red "Error: Couldn't find app.yaml. \nPlease run this script from the //sandbox/feature-registry-app directory."; exit 1; }

# Users: Make sure you have a ./deploy_config.sh file that sets the necessary variables for this script.
[ -f "./deploy_config.sh" ] || {
cat <<EOF > deploy_config.sh
# Path to a folder in the workspace. E.g. /Workspace/Users/Path/To/App/Code
export DEST=""
# Name of the App to deploy. E.g. your-app-name
export APP_NAME=""
EOF
echo_red "Please update deploy_config.sh and run again."
exit 1;
}
source ./deploy_config.sh

databricks sync --full ./src $DEST
databricks apps deploy $APP_NAME --source-code-path $DEST
