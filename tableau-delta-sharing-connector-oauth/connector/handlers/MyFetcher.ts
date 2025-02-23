import { 
  Fetcher,
  FetchOptions,
  FetchUtils,
  getAuthHeader,
  getOAuthHeader,
  log
} from '@tableau/taco-toolkit/handlers'
import { Table } from '../app/utils'

async function getTableMetadata (
  base_url: string,
  token: string,
  share: string,
  schema: string,
  table: string,
  sqlFilters: string[],
  rowLimit: Number
): Promise<any[]> {
  const url = `${base_url}/shares/${share}/schemas/${schema}/tables/${table}/query`
  const headers = getAuthHeader(token)
  // add filtering properties to request body if they exist
  const body = {
    ...(sqlFilters && { 'predicateHints': sqlFilters }),
    ...(rowLimit && { 'limitHint': rowLimit })
  }
  const resp = await FetchUtils.fetchArrayBuffer(url, {
    method: 'POST',
    headers: {
      ...headers,
      'User-Agent': 'Delta-Sharing-Tableau/1.0.1',
      'Content-Type': 'application/json',
      'Custom-Header-Recipient-Id': 'b7e4417a-1f10-4691-b197-445d3588f401'
    },
    body: JSON.stringify(body)
  })
  // resp not guaranteed to be json obj
  // convert binary response to utf8 string and split json objects by newline
  // arr length will be 1 larger since response includes an extra newline at the end
  const rawString = Buffer.from(resp).toString('utf8') 
  const stringArr = rawString.split(new RegExp("\r\n|\r|\n")) 
  
  const fileDataObjArr = new Array(stringArr.length - 3)
  for (let i = 2; i < stringArr.length - 1; i++) {
    fileDataObjArr[i-2] = JSON.parse(stringArr[i])
  }
    
  return fileDataObjArr
}

/*
    * Returns the url of the data table file
    * @param fileDataObjArr - array of file data objects
    * @returns url of data table file
    * TODO: handle multiple data table files after Tableau support is added
*/
function getDataTableUrls(fileDataObjArr: any[]): string[]{
  const dataTableUrls: string[] = [];

  // get s3 files
  for (const dataObj of fileDataObjArr) {
    if (dataObj.file) {
      dataTableUrls.push(dataObj.file.url);
    }
  }

  if (dataTableUrls.length === 0) {
    log('No data table urls found.');
  } else if (dataTableUrls.length > 1) {
    log('More than one data table url found. Only using first url.');
  }
  return dataTableUrls;
}


export default class MyFetcher extends Fetcher {
  async *fetch({ handlerInput, secrets }: FetchOptions) {
    const endpoint = handlerInput.data.endpoint
    const tables: Table[] = handlerInput.data.tables
    const sqlFilters = handlerInput.data.sqlFilters
    const rowLimit = handlerInput.data.rowLimit
    if (secrets) {
      // During multiple restart of the fetcher, it seems the oauth token in secrets will get lost
      // the only remaining thing is the handlerInput
      const token = handlerInput.data.token
      // secrets is guaranteed to "exist" but may still not have bearer token field

      const tableMetaData = await getTableMetadata(endpoint, token, tables[0].share, tables[0].schema, tables[0].name, sqlFilters, rowLimit)

      const dataTableUrls = getDataTableUrls(tableMetaData)

      const promises = dataTableUrls.map((url) => FetchUtils.loadParquetData(url))
      await Promise.all(promises)
      yield

    }
  }
}
