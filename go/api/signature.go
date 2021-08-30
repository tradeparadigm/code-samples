package main

import (
	"bytes"
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"time"
)

// To execute:
// > go run signature.go <Paradigm API_KEY> <Paradigm Secret>

const HOST = "https://api.test.paradigm.co"

func sign(method string, path string, secret string, message string) (string, string, error) {
	secretBase64, err := base64.StdEncoding.DecodeString(secret)
	if err != nil {
		return "", "", err
	}
	timestampStr := strconv.FormatInt(time.Now().UnixMilli(), 10)
	data := timestampStr + "\n" + method + "\n" + path + "\n" + message
	h := hmac.New(sha256.New, secretBase64)
	h.Write([]byte(data))
	signature := base64.StdEncoding.EncodeToString(h.Sum(nil))
	return timestampStr, signature, nil
}

func call(url, method, path, accessKey, secret, message string) (map[string]interface{}, error) {
	client := &http.Client{
		Timeout: time.Second * 10,
	}

	request, err := http.NewRequest(method, url+path, bytes.NewBuffer([]byte(message)))
	if err != nil {
		return nil, err
	}

	//Sign the request
	timestamp, signature, err := sign(method, path, secret, message)
	if err != nil {
		return nil, err
	}

	//Assign headers
	request.Header.Set("Authorization", "Bearer "+accessKey)
	request.Header.Set("Paradigm-API-Timestamp", timestamp)
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Paradigm-API-Signature", signature)

	//Send the request
	response, err := client.Do(request)
	if err != nil {
		return nil, err
	}

	var result map[string]interface{}

	err = json.NewDecoder(response.Body).Decode(&result)
	if err != nil {
		return nil, err
	}

	return result, nil
}

func main() {
	args := os.Args[1:]
	if len(args) != 2 {
		fmt.Printf("Usage <API key> <Secret>")
		return
	}

	accessKey, secret := args[0], args[1]
	method := "POST"
	path := "/echo/"
	message := "{\"message\": \"hello\"}"
	result, err := call(HOST, method, path, accessKey, secret, message)
	if err != nil {
		log.Fatal(err)
	}
	// Print the response
	log.Println(result)
}
