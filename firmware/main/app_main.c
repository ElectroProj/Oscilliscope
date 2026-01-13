#include <stdio.h>
#include <string.h>
#include <math.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/adc.h"
#include "driver/i2s.h"
#include "esp_log.h"
#include "sdkconfig.h"

/*
 * esp32-mini-scope firmware
 *
 * Continuously samples an ADC1 channel via the I²S peripheral in DMA mode
 * and streams frames over UART.  The sample rate, frame length, gain, and
 * offset are configurable via Kconfig and menuconfig.  The binary packet
 * format is documented in docs/protocol.md.
 */

#define TAG "mini_scope"

/* Default values if configuration options are missing (should be set via Kconfig) */
#ifndef CONFIG_MINI_SCOPE_SAMPLE_RATE
#define CONFIG_MINI_SCOPE_SAMPLE_RATE 200000
#endif
#ifndef CONFIG_MINI_SCOPE_FRAME_SAMPLES
#define CONFIG_MINI_SCOPE_FRAME_SAMPLES 1024
#endif
#ifndef CONFIG_MINI_SCOPE_ADC_GAIN
#define CONFIG_MINI_SCOPE_ADC_GAIN 1.0f
#endif
#ifndef CONFIG_MINI_SCOPE_ADC_OFFSET
#define CONFIG_MINI_SCOPE_ADC_OFFSET 0
#endif

/* Choose an ADC1 channel; default is GPIO34 (ADC1_CH6).  Change this define to sample a different pin. */
#ifndef MINI_SCOPE_ADC_CHANNEL
#define MINI_SCOPE_ADC_CHANNEL ADC1_CHANNEL_6
#endif

/* I²S port to use */
#define I2S_PORT            I2S_NUM_0

/* DMA buffer configuration */
#define DMA_BUF_COUNT       4
#define DMA_BUF_LEN         CONFIG_MINI_SCOPE_FRAME_SAMPLES

typedef struct __attribute__((packed)) {
    char magic[4];
    uint32_t frame_counter;
    uint16_t sample_count;
    uint16_t flags;
} scope_pkt_hdr_t;

/* Unpack ADC data from I²S: mask to 12 bits */
static inline uint16_t adc_unpack_12bit(uint16_t s)
{
    return (uint16_t)(s & 0x0FFF);
}

static void scope_i2s_init(void)
{
    /* Configure ADC width and attenuation.  We use 12-bit width and 11 dB attenuation
     * to map roughly 0–3.3 V into the full ADC range. */
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(MINI_SCOPE_ADC_CHANNEL, ADC_ATTEN_DB_11);

    /* Configure I²S for ADC capture.  Only RX is used. */
    i2s_config_t i2s_config = {
        .mode = I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_ADC_BUILT_IN,
        .sample_rate = CONFIG_MINI_SCOPE_SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_I2S_MSB,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = DMA_BUF_COUNT,
        .dma_buf_len = DMA_BUF_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };

    ESP_ERROR_CHECK(i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL));
    ESP_ERROR_CHECK(i2s_set_adc_mode(ADC_UNIT_1, MINI_SCOPE_ADC_CHANNEL));
    ESP_ERROR_CHECK(i2s_adc_enable(I2S_PORT));

    ESP_LOGI(TAG, "I²S ADC initialised: sample_rate=%d Hz, frame_samples=%d", CONFIG_MINI_SCOPE_SAMPLE_RATE, CONFIG_MINI_SCOPE_FRAME_SAMPLES);
}

void app_main(void)
{
    scope_i2s_init();

    static uint16_t i2s_words[CONFIG_MINI_SCOPE_FRAME_SAMPLES];
    static uint16_t samples[CONFIG_MINI_SCOPE_FRAME_SAMPLES];

    uint32_t frame_counter = 0;

    while (true) {
        size_t bytes_read = 0;
        /* Read a frame’s worth of words from I²S.  The driver will block until data is available. */
        esp_err_t err = i2s_read(I2S_PORT, (void *)i2s_words, sizeof(i2s_words), &bytes_read, portMAX_DELAY);
        if (err != ESP_OK || bytes_read == 0) {
            ESP_LOGW(TAG, "i2s_read failed: err=%d bytes=%u", (int)err, (unsigned)bytes_read);
            continue;
        }

        int words = bytes_read / sizeof(uint16_t);
        int n = (words < CONFIG_MINI_SCOPE_FRAME_SAMPLES) ? words : CONFIG_MINI_SCOPE_FRAME_SAMPLES;

        /* Unpack and apply calibration */
        for (int i = 0; i < n; i++) {
            uint16_t raw = adc_unpack_12bit(i2s_words[i]);
            float scaled = (float)raw * CONFIG_MINI_SCOPE_ADC_GAIN + (float)CONFIG_MINI_SCOPE_ADC_OFFSET;
            if (scaled < 0.0f) {
                scaled = 0.0f;
            }
            if (scaled > 4095.0f) {
                scaled = 4095.0f;
            }
            samples[i] = (uint16_t)scaled;
        }

        /* Prepare header */
        scope_pkt_hdr_t hdr;
        memcpy(hdr.magic, "SCOP", 4);
        hdr.frame_counter = frame_counter++;
        hdr.sample_count = (uint16_t)n;
        hdr.flags = 0;

        /* Write header and payload to stdout (UART).  Using stdout ensures that data goes
         * through the same channel as ESP‑IDF monitor when monitor is detached. */
        size_t written = fwrite(&hdr, 1, sizeof(hdr), stdout);
        (void)written;
        written = fwrite(samples, sizeof(uint16_t), n, stdout);
        (void)written;
        fflush(stdout);

        /* Optional: yield to avoid starving other tasks.  Adjust delay as necessary. */
        vTaskDelay(pdMS_TO_TICKS(1));
    }
}
