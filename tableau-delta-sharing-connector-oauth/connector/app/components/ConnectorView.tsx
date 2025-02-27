import 'react-checkbox-tree/lib/react-checkbox-tree.css';
import 'font-awesome/css/font-awesome.min.css';
import React, { useState, useEffect } from 'react'
import CheckboxTree from 'react-checkbox-tree'
import useConnector from './useConnector'
import { Logger } from '@tableau/taco-toolkit';


 
const ConnectorView = () => {
  const { 
    isSubmitting,
    errorMessage,
    isInitializing,
    hasCreds,
    deltaShareStructure,
    oauthCredentials,

    handleSubmit,
    handleCreds,
  } = useConnector()
  const [creds, setCreds] = useState({
    endpoint: '',
    bearerToken: '',
  })
  const [sqlFilters, setSqlFilters] = useState([] as string[])
  const [rowLimit, setRowLimit] = useState('')
  const [checked, setChecked] = useState([] as string[])
  const [expanded, setExpanded] = useState([] as string[])

  const credsInputHandler = (e: React.FormEvent<HTMLInputElement>) => {
    const { name, value } = e.currentTarget;
    setCreds({
      endpoint: creds.endpoint,
      bearerToken: creds.bearerToken,
      [name]: value
    })
  }
  const sqlInputHandler = (e: React.FormEvent<HTMLInputElement>) => {
    setSqlFilters([e.currentTarget.value])
  }
  const shareFileInputHandler = (e: React.FormEvent<HTMLInputElement>) => {
    const file = e.currentTarget.files ? e.currentTarget.files[0] : null
    if (!file) {
      return
    }
    const read = new FileReader()
    read.onloadend = () => {
      const data = read.result?.toString()
      const creds = data ? JSON.parse(data) : null
      if (creds) {
        setCreds(creds)
      }
    }
    read.readAsText(file)
  } 
  const rowLimitInputHandler = (e: React.FormEvent<HTMLInputElement>) => {
    // regex test for numbers only
    const re = /^[0-9\b]+$/
    // if not blank, test regex
    if (e.currentTarget.value === '' || re.test(e.currentTarget.value)) {
      setRowLimit(e.currentTarget.value)
    }
  }

  const onSubmit = () => {
    handleSubmit(checked, sqlFilters, rowLimit)
  }
  const onSendCreds = () => {
    handleCreds(creds.endpoint, creds.bearerToken);

  }
  
  const uniqueSelection = (selected: string[]) => {
    const diff = selected.filter(x => !checked.includes(x))
    setChecked(diff)
  }

    // UseEffect to set creds.token to accessToken when available
    useEffect(() => {
      if (oauthCredentials?.accessToken) {
        setCreds((prevCreds) => ({
          ...prevCreds,
          bearerToken: oauthCredentials.accessToken ?? '',  // Automatically set accessToken to creds.token
        }));
      }
    }, [oauthCredentials]);

  if (isInitializing) {
    return <div className="p-3 text-muted text-center">Initializing...</div>
  }

  if (!hasCreds) {
    return (
      <>
        <div className="box m-auto">
          <div className="card">
            <div className="card-header">
              Sharing Server Credentials
            </div>

            <form className="card-body">

              <label htmlFor="endpoint" className="form-label">Endpoint URL</label>
              <input key="endpoint" name="endpoint" onChange={credsInputHandler} value={creds.endpoint} className="form-control mb-2" placeholder="https://sharing.delta.io/delta-sharing"/>

     
              <label htmlFor="bearerToken" className="form-label">Bearer Token</label>
              <input key="bearerToken" name="bearerToken" onChange={credsInputHandler} value={creds.bearerToken} className="form-control mb-3" placeholder="" type="password"/>

              <div className="or mb-3"> or </div>

              <div className="input-group custom-file-button">
                <label className="input-group-text" htmlFor="inputGroupFile">Upload share file</label>
                <input type="file" className="form-control" id="inputGroupFile" accept=".share" onChange={shareFileInputHandler}/>
              </div>

            </form>
          </div>
          <div className=" text-center">
            <button type="button" className="btn btn-success" onClick={onSendCreds} disabled={isSubmitting}> 
              { isInitializing ? 'Initializing...' : (isSubmitting ? 'Loading tables...' : 'Get Data') }
            </button>
          </div>
          {errorMessage && <div className="alert alert-danger">{errorMessage}</div>}

        </div>
      </>
    )
  }

  return (
    <>
      <div className="box m-auto">
        <div className="card browser-card">
          <div className="card-header">
            Data Explorer
          </div>
          <div className="card-body">
            {
              deltaShareStructure ? 
              <CheckboxTree
                nodes={deltaShareStructure}
                checked={checked}
                expanded={expanded}
                onlyLeafCheckboxes={true}
                expandOnClick={true}
                onCheck={uniqueSelection}
                onExpand={expanded => setExpanded(expanded)}
                iconsClass="fa5"
                />
              :
              <div className="d-flex justify-content-center">
                <div className="spinner-border" role="status">
                  <span className="sr-only">Loading...</span>
                </div>
              </div>
            }

          </div>
        </div>

        <div className="card">
          <div className="card-header">
            Filtering
          </div>
          <form className="card-body">
            <label htmlFor="sqlFilter" className="form-label">SQL Filter</label>
            <input key="sqlFilter" onChange={sqlInputHandler} value={sqlFilters[0]} className="form-control mb-2" placeholder="eg. date >= '2021-01-01' AND magnitude <= 5.3"/> 

            <label htmlFor="rowFilter" className="form-label">Row Limit</label>
            <input key="rowFilter" onChange={rowLimitInputHandler} value={rowLimit} className="form-control mb-3" placeholder="eg. 234"/>
          </form>
        </div>

        <div className="text-center">
          <button type="button" className="btn btn-success" onClick={onSubmit} disabled={isSubmitting || checked.length === 0}> 
            Get Table Data
          </button>
        </div>
      </div>
    </>
  )
}

export default ConnectorView
