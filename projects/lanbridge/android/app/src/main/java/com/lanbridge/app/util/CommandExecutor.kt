package com.lanbridge.app.util

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.net.Uri
import android.os.Build
import android.view.KeyEvent
import android.widget.Toast
import com.lanbridge.app.net.BridgeApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.concurrent.TimeUnit

object CommandExecutor {
    fun getClipboardText(context: Context): String {
        return try {
            val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.primaryClip?.getItemAt(0)?.coerceToText(context)?.toString().orEmpty()
        } catch (_: Exception) { "" }
    }

    fun setClipboardText(context: Context, text: String) {
        try {
            val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newPlainText("LanBridge", text))
        } catch (_: Exception) {}
    }

    suspend fun execute(context: Context, command: JSONObject, api: BridgeApi?): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        val action = command.optString("action")
        val payload = command.optJSONObject("payload") ?: JSONObject()
        try {
            when (action) {
                "open_url" -> {
                    val url = payload.optString("url")
                    if (!url.startsWith("http://") && !url.startsWith("https://")) return@withContext false to "Invalid URL"
                    val i = Intent(Intent.ACTION_VIEW, Uri.parse(url)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    context.startActivity(i)
                    true to "Opened URL"
                }
                "notify" -> {
                    val msg = payload.optString("message", payload.optString("text", "Command executed"))
                    withContext(Dispatchers.Main) { Toast.makeText(context, msg, Toast.LENGTH_SHORT).show() }
                    true to "Notification shown"
                }
                "clipboard_set" -> {
                    val text = payload.optString("text", "")
                    setClipboardText(context, text)
                    api?.setClipboard(text)
                    true to "Clipboard set"
                }
                "clipboard_get", "clipboard_push" -> {
                    val text = getClipboardText(context)
                    api?.setClipboard(text)
                    true to "Clipboard pushed (${text.length} chars)"
                }
                "media" -> {
                    val cmd = payload.optString("cmd", payload.optString("action", "play_pause"))
                    val ok = sendMediaCommand(context, cmd)
                    if (ok) true to "Media: $cmd" else false to "Media command not handled: $cmd"
                }
                "shell" -> {
                    // Runs in app sandbox as app user. argv array required; no shell interpolation.
                    val argvJson = payload.optJSONArray("argv") ?: return@withContext false to "argv array required"
                    val argv = ArrayList<String>(argvJson.length())
                    for (i in 0 until argvJson.length()) argv.add(argvJson.optString(i))
                    if (argv.isEmpty()) return@withContext false to "Empty argv"
                    val proc = ProcessBuilder(argv).redirectErrorStream(true).start()
                    val finished = proc.waitFor(20, TimeUnit.SECONDS)
                    if (!finished) { proc.destroyForcibly(); return@withContext false to "Timeout" }
                    val out = BufferedReader(InputStreamReader(proc.inputStream)).use { it.readText() }
                    val trimmed = if (out.length > 4000) out.takeLast(4000) else out
                    (proc.exitValue() == 0) to "exit=${proc.exitValue()} ${trimmed}".trim()
                }
                else -> false to "Unsupported action: $action"
            }
        } catch (e: Exception) {
            false to (e.message ?: "error")
        }
    }

    private fun sendMediaCommand(context: Context, cmd: String): Boolean {
        return try {
            val am = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            val key = when (cmd.lowercase()) {
                "play" -> KeyEvent.KEYCODE_MEDIA_PLAY
                "pause" -> KeyEvent.KEYCODE_MEDIA_PAUSE
                "play_pause", "play-pause", "toggle" -> KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE
                "next" -> KeyEvent.KEYCODE_MEDIA_NEXT
                "previous", "prev" -> KeyEvent.KEYCODE_MEDIA_PREVIOUS
                "stop" -> KeyEvent.KEYCODE_MEDIA_STOP
                else -> null
            } ?: return false
            am.dispatchMediaKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN, key))
            am.dispatchMediaKeyEvent(KeyEvent(KeyEvent.ACTION_UP, key))
            true
        } catch (_: Exception) { false }
    }
}
