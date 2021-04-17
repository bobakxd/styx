function revokeTokenRequest(username, tokenId, onSuccessCallback) {
    let data = new FormData();
    data.append('action', 'revoke_token')
    data.append('token_id', tokenId)
    let endPoint = `/${encodeURIComponent(username)}/settings/tokens`

    fetch(endPoint, {
        method: 'POST',
        body: data
    }).then(response => {
        if (response.ok) {
            onSuccessCallback()
        }
    })
}

function deleteTokenRow(tokenId) {
    let rowElemId = `token${tokenId}`
    let elem = document.getElementById(rowElemId)
    return elem.parentNode.removeChild(elem)
}
