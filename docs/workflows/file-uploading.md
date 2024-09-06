# File uploading

## Steps

- Get operation type meta.
- Split file into chunks.
- Check if chunk lenght is less than `max_chunks` or `null`.
- Upload each chunk.
- Process the file and send the metadata if required.
- If the file is not processed automatically you should pass the file id to another endpoint.

### Notes

- For user uploading, use `/v2/media/me/chunk` and `/v2/media/me/chunk/upload`.
- For academy uploading, use `/v2/media/academy/chunk` and `/v2/media/academy/chunk/upload` with the `Academy` header.
- Status `TRANSFERRING` means that the file is being processed.
- Status `CREATED` means that the `file.id` must be provided to another endpoint for processing.

## Get available operation types

### Request

```http
GET /v2/media/operationtype HTTP/1.1
Host: breathecode.herokuapp.com
```

### Response

```json
[
    "media",
    "proof-of-payment"
]
```

## Get operation type meta

### Request

```http
GET /v2/media/operationtype/media HTTP/1.1
Host: breathecode.herokuapp.com
```


### Response

```json
{
    "chunk_size": 10485760,
    "max_chunks": null
}
```

## Upload chunk

### Request

```http
POST /v2/media/me/chunk HTTP/1.1
Host: breathecode.herokuapp.com
Content-Type: multipart/form-data; boundary=...

{
    "operation_type": "media",
    "total_chunks": 3,
    "chunk": chunk,
    "chunk_index": 0
}
```

### Response

```json
{
    "academy": null,
    "chunk_index": 0,
    "mime": "image/png",
    "name": "chunk.png",
    "operation_type": "media",
    "total_chunks": 3,
    "user": 1
}
```

## End file uploading and ask for processing

### Request

```http
POST /v2/media/me/chunk/upload HTTP/1.1
Host: breathecode.herokuapp.com
Content-Type: application/json

{
    "operation_type": "media",
    "total_chunks": 3,
    "filename": "chunk.png",
    "mime": "image/png",
    "meta": "{\"slug\":\"my-media\",\"name\":\"my-name\",\"categories\":[\"my-category\"],\"academy\":1}"
}
```

### Response

```json
{
    "id": 1,
    "academy": null,
    "mime": "image/png",
    "name": "a291e39ac495b2effd38d508417cd731",
    "operation_type": "media",
    "user": 1,
    "status": "TRANSFERRING"
}
```
