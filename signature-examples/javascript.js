var CryptoJS = require("crypto-js");

let access_key="JLmxdvhLYIoK0hxgTbTHY6TS"
let secret_key="dOcvUlBXuEE7SHYK8H/5hK/TWXj6lQwnbk/Hl0T0bPu2MonV"

const host="https://api.testnet.paradigm.trade"
const path='/v1/echo'
const method='GET'
const body = ""

var myHeaders = new Headers();
myHeaders.append("Accept", "application/json");
myHeaders.append("Authorization", `Bearer ${access_key}`);

function toHex (str) {
    //src: https://stackoverflow.com/a/62635919/2114395
    var result = '';
    for (var i=0; i<str.length; i++) {
            if (str.charCodeAt(i).toString(16).length === 1) {
                    result += '0' + str.charCodeAt(i).toString(16);
            } else {
                    result += str.charCodeAt(i).toString(16);
            }
    }
    return result;
}


utils = {

  signRequest: function (key) {
    // ms unix time epoch UTC
    const timestamp = new Date().getTime();
    const message = [timestamp, method, path, body].join("\n");

    let decodedKey = CryptoJS.enc.Hex.parse(toHex(atob(key)));

    const signature = CryptoJS.HmacSHA256(message, decodedKey);
    const signature_base64 = CryptoJS.enc.Base64.stringify(signature);

    return { timestamp: timestamp, signature: signature_base64 };
  }
}

let signed = utils.signRequest(secret_key)
myHeaders.append("Paradigm-API-Timestamp", signed.timestamp);
myHeaders.append("Paradigm-API-Signature", signed.signature);


var requestOptions = {
  method: method,
  headers: myHeaders,
  redirect: 'follow'
};

fetch(host+path, requestOptions)
  .then(response => response.text())
  .then(result => console.log(result))
  .catch(error => console.log('error', error));
