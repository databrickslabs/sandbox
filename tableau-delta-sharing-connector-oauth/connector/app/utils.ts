import { Logger, Connector, AjaxResponse } from '@tableau/taco-toolkit'
import { Node } from 'react-checkbox-tree'

interface Share {
  name: string;
  id?: string; 
}

interface Schema {
  name: string;
  share: string;
}

export interface Table {
  name: string;
  schema: string;
  share: string;
  shareId?: string;
  id?: string;
}

async function getResource(connector: Connector, url: string, token: string) {
  const headers = {
    Authorization: `Bearer ${token}`,
    'User-Agent': 'Delta-Sharing-Tableau/1.0.1' 
}
  let resp = await connector.get(url, {
    headers: headers,
    bypassCorsPolicy: true,
  })

  if (!resp.ok) {
    const { errCode, errMsg } = resp.body
    Logger.info("Err getting resource")
    Logger.info(resp)
    Logger.error(resp)
    throw new Error(`Error Code: ${errCode}, Message: ${errMsg}`);
  }

  return resp
}

export async function getShareNames (connector: Connector, base_url: string, token: string, maxResults=10) {
  let shareNames: string[]
  let url = `${base_url}/shares?maxResults=${maxResults}`
  let resp: AjaxResponse = await getResource(connector, url, token)

  if (!resp.body.items) {
    return []
  }
  shareNames = resp.body.items.map((shareObj: Share) => shareObj.name)

  // check for additional pagination results
  let nextPageToken = resp.body.nextPageToken
  while (nextPageToken) {
    url = `${base_url}/shares?maxResults=${maxResults}&pageToken=${nextPageToken}`
    resp = await getResource(connector, url, token)

    nextPageToken = resp.body.nextPageToken
    const respShareNames = resp.body.items.map((shareObj: Share) => shareObj.name)
    shareNames.push(...respShareNames)
  }

  return shareNames
}

export async function getSchemaNames (connector: Connector, base_url: string, token: string, share: string, maxResults=10) {
  let schemaNames: string[]
  let url = `${base_url}/shares/${share}/schemas?maxResults=${maxResults}`
  let resp: AjaxResponse = await getResource(connector, url, token)

  if (!resp.body.items) {
    Logger.info(resp.body.items)
    return []
  }
  schemaNames = resp.body.items.map((schemaObj: Schema) => schemaObj.name)

  // check for addtional pagination results
  let nextPageToken = resp.body.nextPageToken
  while (nextPageToken) {
    url = `${base_url}/shares/${share}/schemas?maxResults=${maxResults}&pageToken=${nextPageToken}`
    resp = await getResource(connector, url, token)

    nextPageToken = resp.body.nextPageToken
    const respSchemaNames = resp.body.items.map((schemaObj: Schema) => schemaObj.name)
    schemaNames.push(...respSchemaNames)
  }

  return schemaNames
}

export async function getTableNamesBySchema (connector: Connector, base_url: string, token: string, share: string, schema: string, maxResults=10) {
  let tableNames: string[]
  let url = `${base_url}/shares/${share}/schemas/${schema}/tables?maxResults=${maxResults}`
  let resp: AjaxResponse = await getResource(connector, url, token)

  if (!resp.body.items) {
    return []
  }
  tableNames = resp.body.items.map((tableObj: Table) => tableObj.name)    

  // check for additional pagination results
  let nextPageToken = resp.body.nextPageToken
  while (nextPageToken) {
    url = `${base_url}/shares/${share}/schemas/${schema}/tables?maxResults=${maxResults}&pageToken=${nextPageToken}`
    resp = await getResource(connector, url, token)

    nextPageToken = resp.body.nextPageToken
    const respTableNames = resp.body.items.map((tableObj: Table) => tableObj.name)
    tableNames.push(...respTableNames)
  }

  return tableNames
}

export async function getTableObjsBySchema (connector: Connector, base_url: string, token: string, share: string, schema: string, maxResults=10) {
  let tableObjs: Table[]
  let url = `${base_url}/shares/${share}/schemas/${schema}/tables?maxResults=${maxResults}`
  let resp: AjaxResponse = await getResource(connector, url, token)

  if (!resp.body.items) {
    return []
  }
  tableObjs = resp.body.items as Table[]

  // check for additional pagination results
  let nextPageToken = resp.body.nextPageToken
  while (nextPageToken) {
    url = `${base_url}/shares/${share}/schemas/${schema}/tables?maxResults=${maxResults}&pageToken=${nextPageToken}`
    resp = await getResource(connector, url, token)

    nextPageToken = resp.body.nextPageToken
    const respTableObjs = resp.body.items as Table[]
    tableObjs.push(...respTableObjs)
  }

  return tableObjs 
}

/*
loads the entire structure at once naively.

returns a tuple containing the Node structure used by react-checkbox-tree and a Map object,
where the keys are denoted by "<share>.<schema>.<table>" and values are Table Objects.

returns: [ Node[], Map<string, Table> ]. The Promise wrapper is for async syntax reasons.
*/
export async function getDeltaShareStructure (connector: Connector, base_url: string, token: string): Promise<[Node[], Map<string, Table>]>{
  let Shares: Node[] = []
  let shareNames: string[] = await getShareNames(connector, base_url, token)
  let tableMap: Map<string, Table> = new Map<string, Table>()

  for (const shareName of shareNames) {
    let Schemas: Node[] = []
    let schemaNames: string[]
    schemaNames = await getSchemaNames(connector, base_url, token, shareName)

    for (const schemaName of schemaNames) {
      let tableObjs: Table[] 
      const schemaString = shareName + "." + schemaName
      tableObjs = await getTableObjsBySchema(connector, base_url, token, shareName, schemaName)

      Schemas.push({
        label: schemaName,
        value: schemaString,
        children: tableObjs.map((tableObj: Table) => {
          const tableString = schemaString + "." + tableObj.name 
          tableMap.set(tableString, tableObj)
          return { label: tableObj.name, value: tableString} as Node
        }), 
      } as Node)
    }

    Shares.push({
      label: shareName,
      value: shareName,
      children: Schemas,
    } as Node)
  }

  return [Shares, tableMap]
}
