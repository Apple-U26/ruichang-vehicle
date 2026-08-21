<template>
  <div class="photo-upload">
    <div class="photo-actions">
      <el-upload
        action="#"
        :auto-upload="false"
        accept="image/*"
        :capture="'environment'"
        :show-file-list="false"
        :disabled="uploading || currentUrls.length >= max"
        :on-change="(file) => enqueue(file.raw)"
      >
        <el-button size="small" :disabled="uploading || currentUrls.length >= max">
          拍照
        </el-button>
      </el-upload>

      <el-upload
        action="#"
        :auto-upload="false"
        accept="image/*"
        multiple
        :show-file-list="false"
        :disabled="uploading || currentUrls.length >= max"
        :on-change="(file) => enqueue(file.raw)"
      >
        <el-button size="small" :disabled="uploading || currentUrls.length >= max">
          相册
        </el-button>
      </el-upload>

      <span class="photo-count">{{ currentUrls.length }}/{{ max }}</span>
    </div>

    <div v-if="currentUrls.length" class="photo-thumbs">
      <div v-for="(url, index) in currentUrls" :key="url" class="thumb-item">
        <img :src="url" alt="" />
        <button
          type="button"
          class="thumb-remove"
          title="删除"
          @click="removeUrl(index)"
        >
          ×
        </button>
      </div>
    </div>

    <AttachmentPreview :url="modelValue" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import AttachmentPreview from './AttachmentPreview.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  max: {
    type: Number,
    default: 6,
  },
})

const emit = defineEmits(['update:modelValue'])
const uploading = ref(false)
const queue = []
let processing = false

const currentUrls = computed(() =>
  String(props.modelValue || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
)

function enqueue(file) {
  if (!file) return
  queue.push(file)
  processQueue()
}

async function processQueue() {
  if (processing) return
  processing = true
  uploading.value = true

  try {
    while (queue.length) {
      if (currentUrls.value.length >= props.max) {
        ElMessage.warning(`最多上传 ${props.max} 张照片`)
        break
      }
      const file = queue.shift()
      await uploadSingle(file)
    }
  } finally {
    processing = false
    uploading.value = false
  }
}

async function uploadSingle(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await request.post('/upload', formData)
  const payload = res.data?.data || res.data || {}
  if (payload.url) {
    const urls = [...currentUrls.value, payload.url].slice(0, props.max)
    emit('update:modelValue', urls.join(','))
  }
}

function removeUrl(index) {
  const urls = [...currentUrls.value]
  urls.splice(index, 1)
  emit('update:modelValue', urls.join(','))
}
</script>

<style scoped>
.photo-upload {
  width: 100%;
}

.photo-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.photo-count {
  color: #999;
  font-size: 12px;
}

.photo-thumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.thumb-item {
  position: relative;
  width: 64px;
  height: 64px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
}

.thumb-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.thumb-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  line-height: 1;
  cursor: pointer;
  font-size: 14px;
}
</style>
