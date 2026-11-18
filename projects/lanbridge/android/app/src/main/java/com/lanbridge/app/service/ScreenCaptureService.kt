package com.lanbridge.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.PixelFormat
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.lanbridge.app.R
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.ByteArrayOutputStream
import java.util.concurrent.atomic.AtomicBoolean

class ScreenCaptureService : Service() {
    companion object {
        const val ACTION_START = "com.lanbridge.app.action.SCREEN_START"
        const val ACTION_STOP = "com.lanbridge.app.action.SCREEN_STOP"
        const val EXTRA_RESULT_CODE = "resultCode"
        const val EXTRA_DATA = "data"
        private const val CHANNEL_ID = "lanbridge_screen"
        private const val NOTIF_ID = 1002
        private val _running = kotlinx.coroutines.flow.MutableStateFlow(false)
        val running = _running
        @Volatile var instance: ScreenCaptureService? = null
    }

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)
    private var projection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var imageReader: ImageReader? = null
    private var job: Job? = null
    private val busy = AtomicBoolean(false)

    private val projectionCallback = if (Build.VERSION.SDK_INT >= 34) object : MediaProjection.Callback() {
        override fun onStop() { stopCapture() }
    } else null

    override fun onCreate() {
        super.onCreate()
        instance = this
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> { stopCapture(); try { stopForeground(STOP_FOREGROUND_REMOVE) } catch (_: Exception) {}; stopSelf(); return START_NOT_STICKY }
            ACTION_START -> {
                val notif = notif("Screen sharing active")
                val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION else 0
                try { ServiceCompat.startForeground(this, NOTIF_ID, notif, type) } catch (_: Exception) { try { startForeground(NOTIF_ID, notif) } catch (_: Exception) {} }
                val code = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
                val data: Intent? = if (Build.VERSION.SDK_INT >= 33) intent.getParcelableExtra(EXTRA_DATA, Intent::class.java) else @Suppress("DEPRECATION") intent.getParcelableExtra(EXTRA_DATA)
                if (code != 0 && data != null) startCapture(code, data) else stopSelf()
            }
        }
        return START_NOT_STICKY
    }

    private fun startCapture(resultCode: Int, data: Intent) {
        if (job != null) return
        try {
            val mpm = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            projection = mpm.getMediaProjection(resultCode, data)
            projectionCallback?.let { cb -> if (Build.VERSION.SDK_INT >= 34) projection?.registerCallback(cb, null) }
            val metrics = resources.displayMetrics
            val density = metrics.densityDpi
            val width = metrics.widthPixels.coerceAtMost(1080).coerceAtLeast(320)
            val height = ((width.toFloat() / metrics.widthPixels.coerceAtLeast(1)) * metrics.heightPixels).toInt().coerceAtMost(2400).coerceAtLeast(480)
            imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
            virtualDisplay = projection?.createVirtualDisplay(
                "LanBridgeScreen", width, height, density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader?.surface, null, null
            )
            _running.value = true
            job = scope.launch {
                var lastSent = 0L
                while (isActive && _running.value) {
                    try {
                        val img = imageReader?.acquireLatestImage()
                        if (img != null) {
                            val now = System.currentTimeMillis()
                            // throttle ~3 fps for LAN stability/low CPU
                            if (now - lastSent >= 330 && busy.compareAndSet(false, true)) {
                                val bitmap = imageToBitmap(img, width, height)
                                try { img.close() } catch (_: Exception) {}
                                lastSent = now
                                scope.launch(Dispatchers.IO) {
                                    try {
                                        val stream = ByteArrayOutputStream()
                                        bitmap.compress(Bitmap.CompressFormat.JPEG, 55, stream)
                                        try { bitmap.recycle() } catch (_: Exception) {}
                                        val bytes = stream.toByteArray()
                                        BridgeConnectionService.instance?.api?.pushScreenJpeg(bytes)
                                    } catch (_: Exception) {
                                    } finally { busy.set(false) }
                                }
                            } else {
                                try { img.close() } catch (_: Exception) {}
                            }
                        }
                    } catch (_: Exception) {}
                    delay(120)
                }
            }
        } catch (_: Exception) {
            stopCapture()
            stopSelf()
        }
    }

    private fun imageToBitmap(image: Image, width: Int, height: Int): Bitmap {
        val plane = image.planes[0]
        val buffer = plane.buffer
        val pixelStride = plane.pixelStride
        val rowStride = plane.rowStride
        val rowPadding = rowStride - pixelStride * width
        val paddedWidth = width + if (pixelStride > 0) rowPadding / pixelStride else 0
        val bmp = Bitmap.createBitmap(paddedWidth.coerceAtLeast(width), height, Bitmap.Config.ARGB_8888)
        bmp.copyPixelsFromBuffer(buffer)
        return if (paddedWidth == width) bmp else {
            val cropped = Bitmap.createBitmap(bmp, 0, 0, width, height)
            if (cropped != bmp) try { bmp.recycle() } catch (_: Exception) {}
            cropped
        }
    }

    private fun stopCapture() {
        _running.value = false
        try { job?.cancel() } catch (_: Exception) {}
        job = null
        busy.set(false)
        try { virtualDisplay?.release() } catch (_: Exception) {}
        try { imageReader?.close() } catch (_: Exception) {}
        try { projectionCallback?.let { cb -> if (Build.VERSION.SDK_INT >= 34) projection?.unregisterCallback(cb) } } catch (_: Exception) {}
        try { projection?.stop() } catch (_: Exception) {}
        virtualDisplay = null; imageReader = null; projection = null
    }

    private fun notif(text: String): Notification = NotificationCompat.Builder(this, CHANNEL_ID)
        .setContentTitle("LanBridge")
        .setContentText(text)
        .setSmallIcon(R.drawable.ic_launcher)
        .setOngoing(true)
        .setOnlyAlertOnce(true)
        .build()

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(CHANNEL_ID, "LanBridge screen sharing", NotificationManager.IMPORTANCE_LOW)
            ch.setShowBadge(false)
            getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null
    override fun onDestroy() { stopCapture(); try { scope.cancel() } catch (_: Exception) {}; instance = null; super.onDestroy() }
}
