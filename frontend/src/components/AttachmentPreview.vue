<template>
  <el-link v-if="urlList.length" type="primary" @click="visible = true">
    查看
  </el-link>
  <span v-else>-</span>

  <teleport to="body">
    <el-image-viewer
      v-if="visible"
      :url-list="urlList"
      hide-on-click-modal
      @close="visible = false"
    />
  </teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElImageViewer } from 'element-plus'

const props = defineProps({
  url: {
    type: String,
    default: '',
  },
  urls: {
    type: Array,
    default: () => [],
  },
})

const visible = ref(false)

const urlList = computed(() => {
  const list = []
  if (props.urls.length) {
    list.push(...props.urls)
  }
  if (props.url) {
    list.push(
      ...String(props.url)
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean)
    )
  }
  return [...new Set(list)]
})
</script>
