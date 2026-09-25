<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import OrderSummary from '../components/OrderSummary.vue'
import TileGridPreview from '../components/TileGridPreview.vue'

const rooms = ref([])
const tiles = ref([])
const selected = ref([])
const tileId = ref(1)
const result = ref(null)
const err = ref('')

onMounted(async () => {
  rooms.value = (await getJSON('/api/rooms')).items.filter(r => r.data_quality === 'clean')
  tiles.value = (await getJSON('/api/tiles')).items.filter(t => t.data_quality === 'clean')
  if (tiles.value.length) tileId.value = tiles.value[0].id
})

const singleLayout = computed(() =>
  result.value?.rooms?.length === 1 ? result.value.rooms[0].layout : null
)

async function run(save) {
  err.value = ''
  try {
    result.value = await postJSON('/api/estimate/batch', {
      room_ids: selected.value,
      tile_id: tileId.value,
      save,
      note: save ? '前端保存' : '',
    })
  } catch (e) {
    err.value = e.message
    result.value = null
  }
}
</script>
<template>
  <div class="page">
    <h1>下单测算</h1>
    <fieldset class="room-picker">
      <legend>房间（可多选，仅清洁房）</legend>
      <label v-for="r in rooms" :key="r.id">
        <input type="checkbox" :value="r.id" v-model="selected" /> {{ r.name }}（{{ r.length }}×{{ r.width }} m）
      </label>
    </fieldset>
    <label>砖型 <select v-model.number="tileId"><option v-for="t in tiles" :key="t.id" :value="t.id">{{ t.name }}</option></select></label>
    <button @click="run(false)">试算</button>
    <button @click="run(true)">保存记录</button>
    <p v-if="err" class="alert">{{ err }}</p>
    <OrderSummary :result="result" />
    <TileGridPreview v-if="singleLayout" :cols="singleLayout.cols" :rows="singleLayout.rows" :grid-count="singleLayout.grid_count" />
  </div>
</template>
