package com.lanbridge.app.ui

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.provider.OpenableColumns
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.lanbridge.app.data.ConnectionConfig
import com.lanbridge.app.data.SavedCommand
import com.lanbridge.app.data.SettingsRepository
import com.lanbridge.app.service.BridgeConnectionService
import com.lanbridge.app.service.LanBridgeAccessibilityService
import com.lanbridge.app.service.ScreenCaptureService
import com.lanbridge.app.ui.theme.*
import com.lanbridge.app.util.CommandExecutor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream

enum class Tab(val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector) {
    Dashboard("Home", Icons.Filled.Home),
    Screen("Screen", Icons.Filled.PhoneAndroid),
    Commands("Commands", Icons.Filled.Terminal),
    Clipboard("Clipboard", Icons.Filled.ContentPaste),
    Files("Files", Icons.Filled.Folder),
    Messages("Inbox", Icons.Filled.Notifications),
    Media("Media", Icons.Filled.MusicNote),
    Settings("Settings", Icons.Filled.Settings)
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LanBridgeApp() {
    val ctx = LocalContext.current
    val repo = remember { SettingsRepository(ctx) }
    var tab by remember { mutableStateOf(Tab.Dashboard) }
    val connStatus by BridgeConnectionService.status.collectAsState()
    val connected by BridgeConnectionService.connected.collectAsState()
    val screenRunning by ScreenCaptureService.running.collectAsState()
    val config by repo.configFlow.collectAsState(initial = ConnectionConfig())

    // Auto-connect in background when configured (keeps service running/reconnecting)
    LaunchedEffect(config.host, config.token) {
        if (config.host.isNotBlank() && config.token.isNotBlank()) {
            try { BridgeConnectionService.start(ctx) } catch (_: Exception) {}
        }
    }

    Scaffold(
        containerColor = Bg,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("LanBridge", fontWeight = FontWeight.Bold)
                        Text(if (connected) connStatus else "Not connected", style = MaterialTheme.typography.labelSmall, color = TextMuted, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                },
                actions = {
                    AssistChip(
                        onClick = {},
                        label = { Text(if (connected) "Connected" else "Offline") },
                        colors = AssistChipDefaults.assistChipColors(
                            containerColor = if (connected) AccentGreen.copy(alpha = 0.18f) else SurfaceAlt,
                            labelColor = if (connected) AccentGreen else TextMuted
                        )
                    )
                    Spacer(Modifier.width(8.dp))
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Bg, titleContentColor = TextPrimary)
            )
        },
        bottomBar = {
            NavigationBar(containerColor = Surface) {
                val tabs = listOf(Tab.Dashboard, Tab.Screen, Tab.Commands, Tab.Clipboard, Tab.Files, Tab.Settings)
                tabs.forEach { t ->
                    NavigationBarItem(
                        selected = tab == t,
                        onClick = { tab = t },
                        icon = { Icon(t.icon, contentDescription = t.label) },
                        label = { Text(t.label, maxLines = 1) },
                        colors = NavigationBarItemDefaults.colors(selectedIconColor = Accent, selectedTextColor = Accent, indicatorColor = SurfaceAlt, unselectedIconColor = TextMuted, unselectedTextColor = TextMuted)
                    )
                }
            }
        }
    ) { pad ->
        Box(Modifier.padding(pad).fillMaxSize()) {
            when (tab) {
                Tab.Dashboard -> DashboardScreen(repo, connected, connStatus, onNavigate = { tab = it })
                Tab.Screen -> ScreenScreen(connected, screenRunning)
                Tab.Commands -> CommandsScreen(repo, connected)
                Tab.Clipboard -> ClipboardScreen(connected)
                Tab.Files -> FilesScreen(connected)
                Tab.Messages -> MessagesScreen()
                Tab.Media -> MediaScreen(connected)
                Tab.Settings -> SettingsScreen(repo)
            }
        }
    }
}

@Composable
fun CardBox(title: String? = null, modifier: Modifier = Modifier, content: @Composable ColumnScope.() -> Unit) {
    Card(modifier = modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Surface), shape = RoundedCornerShape(14.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            if (title != null) Text(title, color = TextMuted, style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold)
            content()
        }
    }
}

@Composable
fun DashboardScreen(repo: SettingsRepository, connected: Boolean, status: String, onNavigate: (Tab) -> Unit) {
    val ctx = LocalContext.current
    val config by repo.configFlow.collectAsState(initial = ConnectionConfig())
    val notifPerm = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        CardBox("Connection") {
            Text(if (connected) "Connected to ${config.host}:${config.port}" else status, color = if (connected) AccentGreen else TextMuted)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    if (Build.VERSION.SDK_INT >= 33) {
                        try { notifPerm.launch(Manifest.permission.POST_NOTIFICATIONS) } catch (_: Exception) {}
                    }
                    try { BridgeConnectionService.start(ctx) } catch (_: Exception) {}
                }, enabled = config.host.isNotBlank() && config.token.isNotBlank()) { Text(if (connected) "Reconnect" else "Connect") }
                OutlinedButton(onClick = { try { BridgeConnectionService.stop(ctx) } catch (_: Exception) {} }, enabled = connected) { Text("Disconnect") }
            }
            if (config.host.isBlank() || config.token.isBlank()) Text("Set PC host and pairing token in Settings first.", color = Warn, style = MaterialTheme.typography.bodySmall)
            else Text("LanBridge runs as a foreground service and will keep trying to reconnect in the background when configured.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
        CardBox("Features") {
            val items = listOf(Tab.Screen to "View/control phone screen", Tab.Commands to "Saved & custom commands", Tab.Clipboard to "Shared clipboard", Tab.Files to "Send and receive files", Tab.Messages to "Notifications & call events", Tab.Media to "Media controls")
            items.forEach { (t, desc) ->
                OutlinedButton(onClick = { onNavigate(t) }, modifier = Modifier.fillMaxWidth()) {
                    Icon(t.icon, null); Spacer(Modifier.width(8.dp)); Column(Modifier.weight(1f), horizontalAlignment = Alignment.Start) { Text(t.label); Text(desc, style = MaterialTheme.typography.labelSmall, color = TextMuted) }
                }
            }
        }
        CardBox("Status & tips") {
            Text("• Same Wi-Fi: use your PC LAN IP and matching token (see TUTORIAL.md).", color = TextMuted, style = MaterialTheme.typography.bodySmall)
            Text("• Enable Accessibility for remote control and Notification access for message/call/media mirroring.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
            Text("• For remote use later, connect both devices through Tailscale instead of exposing ports.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun ScreenScreen(connected: Boolean, screenRunning: Boolean) {
    val ctx = LocalContext.current
    val mpm = ctx.getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
    val launcher = rememberLauncherForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
        if (result.resultCode == Activity.RESULT_OK && result.data != null) {
            val i = Intent(ctx, ScreenCaptureService::class.java).apply {
                action = ScreenCaptureService.ACTION_START
                putExtra(ScreenCaptureService.EXTRA_RESULT_CODE, result.resultCode)
                putExtra(ScreenCaptureService.EXTRA_DATA, result.data)
            }
            ctx.startForegroundService(i)
        }
    }
    Column(Modifier.fillMaxSize().padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        CardBox("Phone screen sharing") {
            Text(if (screenRunning) "Sharing screen frames to PC." else "Start sharing so the PC can view your phone screen.", color = if (screenRunning) AccentGreen else TextMuted)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = {
                    try { launcher.launch(mpm.createScreenCaptureIntent()) } catch (_: Exception) {}
                }, enabled = connected && !screenRunning) { Text("Start sharing") }
                OutlinedButton(onClick = {
                    try { ctx.startService(Intent(ctx, ScreenCaptureService::class.java).setAction(ScreenCaptureService.ACTION_STOP)) } catch (_: Exception) {}
                }, enabled = screenRunning) { Text("Stop") }
            }
            if (!connected) Text("Connect to PC first.", color = Warn, style = MaterialTheme.typography.bodySmall)
        }
        CardBox("Remote control") {
            val enabled by LanBridgeAccessibilityService.enabled.collectAsState()
            Text(if (enabled) "Accessibility service is enabled. PC can send taps/swipes/navigation." else "Accessibility service is not enabled. PC view works, but remote control needs Accessibility.", color = if (enabled) AccentGreen else Warn)
            OutlinedButton(onClick = {
                try { ctx.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) {}
            }) { Text("Open Accessibility settings") }
            Text("In Accessibility settings, open Installed apps/downloaded services → LanBridge and turn it on. Return to this screen after enabling; status updates when the service connects.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
        CardBox("Notes") {
            Text("Screen capture requires approving the system prompt each session. Some apps may appear blank due to secure/DRM flags.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
fun CommandsScreen(repo: SettingsRepository, connected: Boolean) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val commands by repo.commandsFlow.collectAsState(initial = emptyList())
    var name by remember { mutableStateOf("") }
    var action by remember { mutableStateOf("open_url") }
    var payloadText by remember { mutableStateOf("{\"url\":\"https://example.com\"}") }
    var statusMsg by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        CardBox("Add saved command") {
            OutlinedTextField(name, { name = it }, label = { Text("Name") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("open_url", "notify", "clipboard_push", "media", "shell").forEach { a ->
                    FilterChip(selected = action == a, onClick = {
                        action = a
                        payloadText = when (a) {
                            "open_url" -> "{\"url\":\"https://example.com\"}"
                            "notify" -> "{\"message\":\"Hello from LanBridge\"}"
                            "clipboard_push" -> "{}"
                            "media" -> "{\"cmd\":\"play_pause\"}"
                            "shell" -> "{\"argv\":[\"/system/bin/sh\",\"-c\",\"echo hi\"]}"
                            else -> "{}"
                        }
                    }, label = { Text(a, maxLines = 1) })
                }
            }
            OutlinedTextField(payloadText, { payloadText = it }, label = { Text("Payload JSON") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
            Button(onClick = {
                val n = name.trim(); if (n.isEmpty()) return@Button
                val payload = try { JSONObject(payloadText.ifBlank { "{}" }) } catch (_: Exception) { JSONObject() }
                val cmd = SavedCommand(id = "cmd_${System.currentTimeMillis()}", name = n, action = action, payload = payload)
                scope.launch { repo.saveCommands(commands + cmd); name = ""; statusMsg = "Saved \"$n\"" }
            }) { Text("Save command") }
            if (statusMsg.isNotBlank()) Text(statusMsg, color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
        Text("Saved commands", fontWeight = FontWeight.SemiBold)
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.weight(1f, fill = true)) {
            items(commands, key = { it.id }) { cmd ->
                Card(colors = CardDefaults.cardColors(containerColor = Surface), shape = RoundedCornerShape(12.dp)) {
                    Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(cmd.name, fontWeight = FontWeight.SemiBold)
                            Text(cmd.action, color = TextMuted, style = MaterialTheme.typography.bodySmall)
                        }
                        TextButton(onClick = {
                            scope.launch {
                                statusMsg = "Running ${cmd.name}…"
                                val result = CommandExecutor.execute(ctx, JSONObject().apply { put("id", cmd.id); put("name", cmd.name); put("action", cmd.action); put("payload", cmd.payload) }, BridgeConnectionService.instance?.api)
                                statusMsg = if (result.first) "OK: ${result.second}" else "Failed: ${result.second}"
                                if (connected) {
                                    withContext(Dispatchers.IO) {
                                        try {
                                            BridgeConnectionService.instance?.api?.postEvent("command_result", JSONObject().put("name", cmd.name).put("ok", result.first).put("message", result.second))
                                        } catch (_: Exception) {}
                                    }
                                }
                            }
                        }) { Text("Run") }
                        TextButton(onClick = { scope.launch { repo.saveCommands(commands.filterNot { it.id == cmd.id }) } }) { Text("Delete", color = Danger) }
                    }
                }
            }
            if (commands.isEmpty()) item { Text("No saved commands yet.", color = TextMuted) }
        }
    }
}

@Composable
fun ClipboardScreen(connected: Boolean) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var text by remember { mutableStateOf("") }
    var msg by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        CardBox("Shared clipboard") {
            OutlinedTextField(text, { text = it }, modifier = Modifier.fillMaxWidth().heightIn(min = 180.dp), label = { Text("Text") })
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                Button(onClick = {
                    scope.launch(Dispatchers.IO) { CommandExecutor.setClipboardText(ctx, text) }
                    msg = "Copied to phone clipboard"
                }, modifier = Modifier.weight(1f)) { Text("Copy local") }
                Button(onClick = {
                    scope.launch {
                        msg = "Sending…"
                        val r = withContext(Dispatchers.IO) { BridgeConnectionService.instance?.api?.setClipboard(text) }
                        msg = if (r?.isSuccess == true) "Sent to PC/shared" else "Send failed: ${r?.exceptionOrNull()?.message ?: "not connected"}"
                    }
                }, enabled = connected, modifier = Modifier.weight(1f)) { Text("Send to PC") }
            }
            OutlinedButton(onClick = {
                scope.launch {
                    msg = "Fetching…"
                    val r = withContext(Dispatchers.IO) { BridgeConnectionService.instance?.api?.getClipboard() }
                    if (r?.isSuccess == true) { text = r.getOrNull().orEmpty(); msg = "Fetched shared clipboard" }
                    else msg = "Fetch failed: ${r?.exceptionOrNull()?.message ?: "not connected"}"
                }
            }, enabled = connected, modifier = Modifier.fillMaxWidth()) { Text("Fetch from PC/shared") }
            if (msg.isNotBlank()) Text(msg, color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
        CardBox("Tip") { Text("PC clipboard updates can also arrive automatically via the connection stream when supported.", color = TextMuted, style = MaterialTheme.typography.bodySmall) }
    }
}

@Composable
fun FilesScreen(connected: Boolean) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf("") }
    var pcFiles by remember { mutableStateOf(listOf<String>()) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        uri ?: return@rememberLauncherForActivityResult
        scope.launch {
            status = "Preparing file…"
            val file = copyUriToCache(ctx, uri)
            if (file == null) { status = "Failed to read file"; return@launch }
            status = "Uploading ${file.name}…"
            val res = withContext(Dispatchers.IO) { BridgeConnectionService.instance?.api?.uploadFile(file) }
            status = if (res?.isSuccess == true) "Sent: ${file.name}" else "Upload failed: ${res?.exceptionOrNull()?.message ?: "not connected"}"
        }
    }
    fun refreshPcFiles() {
        scope.launch {
            val res = withContext(Dispatchers.IO) { BridgeConnectionService.instance?.api?.listPcFiles() }
            if (res?.isSuccess == true) {
                val arr = res.getOrNull()
                val list = mutableListOf<String>()
                if (arr != null) for (i in 0 until arr.length()) { arr.optJSONObject(i)?.optString("name")?.let { if (it.isNotBlank()) list.add(it) } }
                pcFiles = list
                status = "Loaded ${list.size} shared file(s)"
            } else if (connected) {
                status = "Could not list PC files: ${res?.exceptionOrNull()?.message}"
            }
        }
    }
    Column(Modifier.fillMaxSize().padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        CardBox("Send to PC") {
            Text("Choose a photo, video, document or any file to upload to the PC download folder.", color = TextMuted)
            Button(onClick = { picker.launch(arrayOf("*/*")) }, enabled = connected) { Icon(Icons.Filled.Upload, null); Spacer(Modifier.width(8.dp)); Text("Pick and send file") }
            if (!connected) Text("Connect to PC first.", color = Warn, style = MaterialTheme.typography.bodySmall)
        }
        CardBox("Receive from PC") {
            Text("Files the PC shared in LanBridge (outgoing) are listed here. Downloads are saved to app files.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { refreshPcFiles() }, enabled = connected) { Text("Refresh list") }
            }
            pcFiles.forEach { name ->
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Text(name, modifier = Modifier.weight(1f), maxLines = 1, overflow = TextOverflow.Ellipsis)
                    TextButton(onClick = {
                        scope.launch {
                            status = "Downloading $name…"
                            val destDir = File(ctx.getExternalFilesDir(null), "downloads").apply { mkdirs() }
                            val dest = File(destDir, name)
                            val res = withContext(Dispatchers.IO) { BridgeConnectionService.instance?.api?.downloadPcFile(name, dest) }
                            status = if (res?.isSuccess == true) "Downloaded to ${dest.absolutePath}" else "Download failed: ${res?.exceptionOrNull()?.message}"
                        }
                    }, enabled = connected) { Text("Download") }
                }
            }
            if (pcFiles.isEmpty()) Text("No files listed yet.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
        if (status.isNotBlank()) Text(status, color = TextMuted, style = MaterialTheme.typography.bodySmall)
    }
}

private fun copyUriToCache(context: Context, uri: Uri): File? {
    return try {
        val name = queryName(context, uri) ?: "upload_${System.currentTimeMillis()}"
        val out = File(context.cacheDir, name.replace(Regex("[^A-Za-z0-9._() -]"), "_"))
        context.contentResolver.openInputStream(uri)?.use { input ->
            FileOutputStream(out).use { output -> input.copyTo(output) }
        } ?: return null
        out
    } catch (_: Exception) { null }
}

private fun queryName(context: Context, uri: Uri): String? {
    return try {
        context.contentResolver.query(uri, null, null, null, null)?.use { c ->
            val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (c.moveToFirst() && idx >= 0) c.getString(idx) else null
        }
    } catch (_: Exception) { null }
}

@Composable
fun MessagesScreen() {
    val ctx = LocalContext.current
    Column(Modifier.fillMaxSize().padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        CardBox("Notifications & calls") {
            Text("Enable Notification access so LanBridge can mirror notifications (including many SMS/call alerts) to the connected PC. Call answering from PC is not supported by stock Android for third-party apps.", color = TextMuted)
            Button(onClick = { ctx.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }) { Text("Open Notification access settings") }
        }
        CardBox("Event stream") {
            Text("Mirrored notification and call events appear in the PC app under Messages & Calls while connected.", color = TextMuted)
        }
    }
}

@Composable
fun MediaScreen(connected: Boolean) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf("") }
    var pcStatus by remember { mutableStateOf("") }
    fun sendPhone(cmd: String) {
        scope.launch {
            val r = CommandExecutor.execute(ctx, JSONObject().apply { put("action", "media"); put("payload", JSONObject().put("cmd", cmd)) }, BridgeConnectionService.instance?.api)
            status = if (r.first) "Phone media: $cmd" else "Failed: ${r.second}"
            if (connected) BridgeConnectionService.instance?.api?.postEvent("media", JSONObject().put("local_command", cmd).put("ok", r.first))
        }
    }
    fun sendPc(cmd: String) {
        scope.launch {
            val res = withContext(Dispatchers.IO) { BridgeConnectionService.instance?.api?.pcMedia(cmd) }
            status = if (res?.isSuccess == true) "PC media: $cmd" else "PC media failed: ${res?.exceptionOrNull()?.message ?: "not connected"}"
        }
    }
    fun refreshPc() {
        scope.launch {
            val res = withContext(Dispatchers.IO) { BridgeConnectionService.instance?.api?.pcMediaStatus() }
            pcStatus = if (res?.isSuccess == true) res.getOrNull()?.toString() ?: "" else "Unavailable: ${res?.exceptionOrNull()?.message ?: "not connected"}"
        }
    }
    Column(Modifier.fillMaxSize().padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        CardBox("Control phone media") {
            Text("Send transport commands to the active media session on this phone.", color = TextMuted)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { sendPhone("previous") }) { Text("Prev") }
                Button(onClick = { sendPhone("play_pause") }) { Text("Play/Pause") }
                OutlinedButton(onClick = { sendPhone("next") }) { Text("Next") }
            }
        }
        CardBox("Control PC media") {
            Text("Controls PC players via MPRIS/playerctl when available on the PC.", color = TextMuted)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { sendPc("previous") }, enabled = connected) { Text("Prev") }
                Button(onClick = { sendPc("play-pause") }, enabled = connected) { Text("Play/Pause") }
                OutlinedButton(onClick = { sendPc("next") }, enabled = connected) { Text("Next") }
            }
            OutlinedButton(onClick = { refreshPc() }, enabled = connected) { Text("Refresh PC status") }
            if (pcStatus.isNotBlank()) Text(pcStatus, color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
        if (status.isNotBlank()) Text(status, color = TextMuted, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
fun SettingsScreen(repo: SettingsRepository) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val current by repo.configFlow.collectAsState(initial = ConnectionConfig())
    var host by remember(current.host) { mutableStateOf(current.host) }
    var port by remember(current.port) { mutableStateOf(current.port.toString()) }
    var token by remember(current.token) { mutableStateOf(current.token) }
    var name by remember(current.deviceName) { mutableStateOf(current.deviceName) }
    var msg by remember { mutableStateOf("") }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(14.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        CardBox("PC connection") {
            OutlinedTextField(host, { host = it }, label = { Text("PC IP or hostname (LAN/Tailscale)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            OutlinedTextField(port, { port = it.filter { c -> c.isDigit() } }, label = { Text("Port") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            OutlinedTextField(token, { token = it }, label = { Text("Pairing token") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            OutlinedTextField(name, { name = it }, label = { Text("This device name") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Button(onClick = {
                val p = port.toIntOrNull()?.coerceIn(1, 65535) ?: 8765
                val cfg = ConnectionConfig(host.trim(), p, token.trim(), name.trim().ifBlank { android.os.Build.MODEL ?: "Android" })
                scope.launch {
                    repo.saveConfig(cfg)
                    msg = "Saved"
                    if (cfg.host.isNotBlank() && cfg.token.isNotBlank()) {
                        try { BridgeConnectionService.start(ctx) } catch (_: Exception) {}
                    }
                }
            }, modifier = Modifier.fillMaxWidth()) { Text("Save settings & connect") }
            if (msg.isNotBlank()) Text(msg, color = AccentGreen)
            Text("After saving with a valid host/token, LanBridge will keep a foreground connection service running and auto-reconnect in background.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
        CardBox("Permissions & access") {
            Text("Grant only what you need: Screen capture prompt (sharing), Accessibility (remote control/taps), Notification access (mirroring), Files/Media (sending).", color = TextMuted, style = MaterialTheme.typography.bodySmall)
            OutlinedButton(onClick = { try { ctx.startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:${ctx.packageName}")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) {} }, modifier = Modifier.fillMaxWidth()) { Text("App info / permissions") }
            OutlinedButton(onClick = { try { ctx.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) {} }, modifier = Modifier.fillMaxWidth()) { Text("Accessibility settings") }
            OutlinedButton(onClick = { try { ctx.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) {} }, modifier = Modifier.fillMaxWidth()) { Text("Notification access settings") }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                OutlinedButton(onClick = {
                    try { ctx.startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) } catch (_: Exception) {}
                }, modifier = Modifier.fillMaxWidth()) { Text("Battery optimization settings") }
            }
            Text("For reliable background connection, disable battery optimizations for LanBridge and allow notifications.", color = TextMuted, style = MaterialTheme.typography.bodySmall)
        }
    }
}
