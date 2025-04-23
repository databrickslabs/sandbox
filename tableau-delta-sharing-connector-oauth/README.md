# databricks-delta-sharing-connector
Databricks's Delta Sharing WDC 3.0 based Connector

The connector is built with the Tableau Web Data Connector 3.0 SDK and provides:
- Share/Schema/Table browsing wihtin a share
- OAuth Authentication

## Prerequisite
- [Python 3.7 or higher](https://www.python.org/downloads/)
- [JDK 11 or higher](https://www.oracle.com/java/technologies/downloads/)
- [Tableau Desktop 2023.3.14 or later](https://www.tableau.com/support/releases/desktop/2023.3.14)
- Install [taco-toolkit](https://help.tableau.com/current/api/webdataconnector/en-us/index.html): `npm install -g @tableau/taco-toolkit@2.0.0`

## Local Test

After cloning and installing npm packages, in the top level directory:

To compile/build project  
```taco build```

To produce .taco file (for Tableau Desktop testing)  
```taco pack```

To run .taco file in top level directory (launches Tableau Desktop, runs interactive phase + data gathering phase)  
```taco run Desktop```

The current connector.json file has an example OAuth setting which target EntraId with your default/home tenant.
If you are using EntraID, you only need to change the tenentId from **common** to your tenantId in the **authUri**/**tokenUri**.
If you are using other Idp you need to follow your Idp guidence of how to register an app and grab the folloing fields: 
- **clientIdDesktop**: The OAuth ClientId target your IDP
- **authUri**: The authentication url for your IDP
- **tokenUri**: The token url for your IDP
- **scopes**: The OAuth scopes to use with your IDP

E.g. for Okta: https://developer.okta.com/docs/guides/implement-oauth-for-okta/main/.

## Run in Tableau
Please refer to [Tableau doc](https://tableau.github.io/connector-plugin-sdk/docs/run-taco)

## Limitations
Please refer to [Databricks doc](https://docs.databricks.com/aws/en/delta-sharing/read-data-open#limitations-of-the-tableau-delta-sharing-connector)