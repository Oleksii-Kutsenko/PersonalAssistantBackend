# Reference for websockets API

### Messages format

Generally message is a json dictionary that have two keys:

|Name|Type|Description|
|---|---|---|
|type|integer|Type helps to control messages and errors flow|
|message|dictionary|Dictionary with requested or required information|

### Message types
|Name|Value|Description|
|---|---|---|
|message|0|Informational message|
|error|1|Message with error|

### Available endpoints

---

`ws://hostname/ws/fin/api/indices/(index_id)/adjusted/`

Adjust index by the money amount, required money amount in message section

Example of request json:

```json
{
  "type": 0,
  "message": {
    "money": 2000
  }
}
```

Example of response json:

```json
{
  "type":0,
  "message":[
    {
      "name":"GE",
      "price":6.95,
      "weight":0.01579663235533376,
      "visible":true
    },
    {
      "name":"XOM",
      "price":34.35,
      "weight":0.039314984737138695,
      "visible":true
    },
    {
      "name":"CMCSA",
      "price":35.91,
      "weight":0.03963981065644846,
      "visible":true
    },
    {
      "name":"BAC",
      "price":20.3,
      "weight":0.04150114899267993,
      "visible":true
    },
    {
      "name":"PFE",
      "price":29.85,
      "weight":0.041517336330851515,
      "visible":true
    },
    {
      "name":"KO",
      "price":44.65,
      "weight":0.04544695399003497,
      "visible":true
    },
    {
      "name":"INTC",
      "price":48.8,
      "weight":0.049514343882989906,
      "visible":true
    },
    {
      "name":"VZ",
      "price":50.4,
      "weight":0.052921495932044836,
      "visible":true
    },
    {
      "name":"T",
      "price":31.83,
      "weight":0.057204254505244544,
      "visible":true
    },
    {
      "name":"FB",
      "price":155.45,
      "weight":0.09291655442589061,
      "visible":true
    },
    {
      "name":"AAPL",
      "price":245.5,
      "weight":0.2591033735748847,
      "visible":true
    },
    {
      "name":"MSFT",
      "price":141.02,
      "weight":0.26512311061645805,
      "visible":true
    }
  ]
}
```

### Extra examples

Retrieve a list

```json
{
  "type": 0,
  "message": [{...}, {...}, {...}]
}
```

Send an information 

```json
{
  "type": 0,
  "message": {"money":  10000}
}
```

Get an error

```json
{
  "type": 1,
  "message": {
    "class": "FormatError",
    "detail": "JSONDecodeErrorExtra: Extra data: line 1 column 3 (char 2)"}
}
```