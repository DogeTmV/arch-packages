package com.lanbridge.app.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import org.json.JSONArray
import org.json.JSONObject

private val Context.dataStore by preferencesDataStore(name = "lanbridge_settings")

data class ConnectionConfig(
    val host: String = "",
    val port: Int = 8765,
    val token: String = "",
    val deviceName: String = android.os.Build.MODEL ?: "Android"
)

data class SavedCommand(
    val id: String,
    val name: String,
    val action: String,
    val payload: JSONObject = JSONObject(),
    val target: String = "phone"
)

class SettingsRepository(private val context: Context) {
    private object Keys {
        val HOST = stringPreferencesKey("host")
        val PORT = stringPreferencesKey("port")
        val TOKEN = stringPreferencesKey("token")
        val DEVICE_NAME = stringPreferencesKey("device_name")
        val COMMANDS = stringPreferencesKey("commands_json")
        val CLIPBOARD = stringPreferencesKey("last_clipboard")
    }

    val configFlow: Flow<ConnectionConfig> = context.dataStore.data.map { prefs ->
        ConnectionConfig(
            host = prefs[Keys.HOST] ?: "",
            port = (prefs[Keys.PORT] ?: "8765").toIntOrNull() ?: 8765,
            token = prefs[Keys.TOKEN] ?: "",
            deviceName = prefs[Keys.DEVICE_NAME] ?: (android.os.Build.MODEL ?: "Android")
        )
    }

    val commandsFlow: Flow<List<SavedCommand>> = context.dataStore.data.map { prefs ->
        parseCommands(prefs[Keys.COMMANDS] ?: "[]")
    }

    suspend fun saveConfig(config: ConnectionConfig) {
        context.dataStore.edit { prefs ->
            prefs[Keys.HOST] = config.host
            prefs[Keys.PORT] = config.port.toString()
            prefs[Keys.TOKEN] = config.token
            prefs[Keys.DEVICE_NAME] = config.deviceName
        }
    }

    suspend fun saveCommands(commands: List<SavedCommand>) {
        val arr = JSONArray()
        commands.forEach { c ->
            arr.put(JSONObject().apply {
                put("id", c.id)
                put("name", c.name)
                put("action", c.action)
                put("payload", c.payload)
                put("target", c.target)
            })
        }
        context.dataStore.edit { prefs -> prefs[Keys.COMMANDS] = arr.toString() }
    }

    private fun parseCommands(raw: String): List<SavedCommand> {
        return try {
            val arr = JSONArray(raw)
            (0 until arr.length()).mapNotNull { i ->
                val o = arr.optJSONObject(i) ?: return@mapNotNull null
                SavedCommand(
                    id = o.optString("id", "cmd_$i"),
                    name = o.optString("name", "Command"),
                    action = o.optString("action", "notify"),
                    payload = o.optJSONObject("payload") ?: JSONObject(),
                    target = o.optString("target", "phone")
                )
            }
        } catch (_: Exception) { emptyList() }
    }
}
