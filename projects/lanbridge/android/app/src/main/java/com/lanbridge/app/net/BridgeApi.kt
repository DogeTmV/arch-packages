package com.lanbridge.app.net

import com.lanbridge.app.data.ConnectionConfig
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

class BridgeApi(var config: ConnectionConfig) {
    private val jsonType = "application/json; charset=utf-8".toMediaType()
    private val binType = "application/octet-stream".toMediaType()
    private val jpegType = "image/jpeg".toMediaType()

    val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(0, TimeUnit.SECONDS) // SSE
        .writeTimeout(20, TimeUnit.SECONDS)
        .build()

    private val shortClient: OkHttpClient = client.newBuilder()
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    fun baseUrl(): String = "http://${config.host}:${config.port}"

    private fun authed(url: String): Request.Builder =
        Request.Builder().url(url).header("Authorization", "Bearer ${config.token}")

    fun pair(): Result<JSONObject> = runCatching {
        val body = JSONObject().apply {
            put("token", config.token)
            put("device", JSONObject().apply {
                put("name", config.deviceName)
                put("platform", "android")
                put("model", android.os.Build.MODEL ?: "")
                put("version", android.os.Build.VERSION.RELEASE ?: "")
            })
        }.toString().toRequestBody(jsonType)
        shortClient.newCall(Request.Builder().url("${baseUrl()}/api/pair").post(body).build()).execute().use { resp ->
            val text = resp.body?.string().orEmpty()
            val obj = if (text.isNotBlank()) JSONObject(text) else JSONObject()
            if (!resp.isSuccessful || !obj.optBoolean("ok", false)) error(obj.optString("error", "HTTP ${resp.code}"))
            obj
        }
    }

    fun postEvent(type: String, payload: JSONObject = JSONObject()): Result<Unit> = runCatching {
        val body = JSONObject().apply { put("type", type); put("payload", payload) }.toString().toRequestBody(jsonType)
        shortClient.newCall(authed("${baseUrl()}/api/events").post(body).build()).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
        }
    }

    fun getClipboard(): Result<String> = runCatching {
        shortClient.newCall(authed("${baseUrl()}/api/clipboard").get().build()).execute().use { resp ->
            val obj = JSONObject(resp.body?.string().orEmpty())
            if (!resp.isSuccessful || !obj.optBoolean("ok", false)) error(obj.optString("error", "HTTP ${resp.code}"))
            obj.optString("text", "")
        }
    }

    fun setClipboard(text: String): Result<Unit> = runCatching {
        val body = JSONObject().apply { put("text", text); put("source", "phone") }.toString().toRequestBody(jsonType)
        shortClient.newCall(authed("${baseUrl()}/api/clipboard").post(body).build()).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
        }
    }

    fun getCommands(): Result<JSONArray> = runCatching {
        shortClient.newCall(authed("${baseUrl()}/api/commands").get().build()).execute().use { resp ->
            val obj = JSONObject(resp.body?.string().orEmpty())
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            obj.optJSONArray("commands") ?: JSONArray()
        }
    }

    fun saveCommands(commands: JSONArray): Result<Unit> = runCatching {
        val body = JSONObject().apply { put("commands", commands) }.toString().toRequestBody(jsonType)
        shortClient.newCall(authed("${baseUrl()}/api/commands").post(body).build()).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
        }
    }

    fun runPcCommand(command: JSONObject): Result<JSONObject> = runCatching {
        val body = JSONObject().apply { put("target", "pc"); put("command", command) }.toString().toRequestBody(jsonType)
        shortClient.newCall(authed("${baseUrl()}/api/commands/run").post(body).build()).execute().use { resp ->
            val obj = JSONObject(resp.body?.string().orEmpty())
            if (!resp.isSuccessful) error(obj.optString("error", "HTTP ${resp.code}"))
            obj
        }
    }

    fun pcMedia(cmd: String): Result<JSONObject> = runCatching {
        val body = JSONObject().apply { put("cmd", cmd) }.toString().toRequestBody(jsonType)
        shortClient.newCall(authed("${baseUrl()}/api/pc/media").post(body).build()).execute().use { resp ->
            val obj = JSONObject(resp.body?.string().orEmpty())
            if (!resp.isSuccessful) error(obj.optString("error", "HTTP ${resp.code}"))
            obj
        }
    }

    fun pcMediaStatus(): Result<JSONObject> = runCatching {
        shortClient.newCall(authed("${baseUrl()}/api/pc/media-status").post("{}".toRequestBody(jsonType)).build()).execute().use { resp ->
            val obj = JSONObject(resp.body?.string().orEmpty())
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            obj.optJSONObject("media") ?: JSONObject()
        }
    }

    fun listPcFiles(): Result<JSONArray> = runCatching {
        shortClient.newCall(authed("${baseUrl()}/api/pc-files").get().build()).execute().use { resp ->
            val obj = JSONObject(resp.body?.string().orEmpty())
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            obj.optJSONArray("files") ?: JSONArray()
        }
    }

    fun downloadPcFile(name: String, dest: File): Result<File> = runCatching {
        val encoded = java.net.URLEncoder.encode(name, "UTF-8")
        shortClient.newCall(authed("${baseUrl()}/api/pc-files/$encoded").get().build()).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            resp.body?.byteStream()?.use { input -> FileOutputStream(dest).use { output -> input.copyTo(output) } } ?: error("Empty body")
            dest
        }
    }

    fun uploadFile(file: File): Result<JSONObject> = runCatching {
        val body = file.readBytes().toRequestBody(binType)
        val req = authed("${baseUrl()}/api/files").post(body)
            .header("X-Filename", file.name)
            .header("Content-Type", "application/octet-stream")
            .build()
        shortClient.newCall(req).execute().use { resp ->
            val obj = JSONObject(resp.body?.string().orEmpty())
            if (!resp.isSuccessful || !obj.optBoolean("ok", false)) error(obj.optString("error", "HTTP ${resp.code}"))
            obj
        }
    }

    fun pushScreenJpeg(bytes: ByteArray): Result<Unit> = runCatching {
        val body = bytes.toRequestBody(jpegType)
        shortClient.newCall(authed("${baseUrl()}/api/screen/push").post(body).header("Content-Type", "image/jpeg").build()).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
        }
    }

    fun openEvents(onEvent: (JSONObject) -> Unit, onFail: (String) -> Unit): EventSource {
        val request = authed("${baseUrl()}/api/events").get().build()
        val factory = EventSources.createFactory(client)
        return factory.newEventSource(request, object : EventSourceListener() {
            override fun onEvent(eventSource: EventSource, id: String?, type: String?, data: String) {
                try { onEvent(JSONObject(data)) } catch (_: Exception) {}
            }
            override fun onFailure(eventSource: EventSource, t: Throwable?, response: Response?) {
                onFail(t?.message ?: "SSE failure ${response?.code ?: ""}")
            }
        })
    }
}
