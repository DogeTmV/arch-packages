package com.lanbridge.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.lanbridge.app.ui.LanBridgeApp
import com.lanbridge.app.ui.theme.LanBridgeTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            LanBridgeTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    LanBridgeApp()
                }
            }
        }
    }
}
