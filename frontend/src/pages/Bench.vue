<script setup>
import { computed, onMounted, ref } from 'vue'
import { getJSON, postJSON } from '../api'
import OrderSummary from '../components/OrderSummary.vue'
import TileGridPreview from '../components/TileGridPreview.vue'

const rooms = ref([])
const tiles = ref([])
const picked = ref([])
const tileId = ref(null)
const wastePct = ref('')
const result = ref(null)
const err = ref('')

onMounted(async () => {
  rooms.value = (await getJSON('/api/rooms')).items.filter(r => r.data_quality === 'clean')
  tiles.value = (await getJSON('/api/tiles')).items.filter(t => t.data_quality === 'clean')
  if (tiles.value.length) tileId.value = tiles.value[0].id
})

const summary = computed(() => {
  const r = result.value
  if (!r) return null
  return {
    order_count: r.total_order_count,
    raw_count: r.total_raw_count,
    waste_pct: r.waste_pct,
    area_m2: r.total_area_m2,
    piece_m2: r.rooms[0]?.piece_m2,
  }
})

async function run(save) {
  err.value = ''
  result.value = null
  const body = { room_ids: picked.value, tile_id: tileId.value, save, note: save ? '前端保存' : '' }
  if (wastePct.value !== '') body.waste_pct = Number(wastePct.value)
  try {
    result.value = await postJSON('/api/estimate/batch', body)
  } catch (e) {
    err.value = e.message
  }
}
</script>
<template>
  <div class="page">
    <h1>下单测算</h1>
    <fieldset class="room-picker">
      <legend>房间（可多选，仅列正常房间）</legend>
      <label v-for="r in rooms" :key="r.id" class="room-option">
        <input type="checkbox" :value="r.id" v-model="picked" /> {{ r.name }}（{{ r.length }}×{{ r.width }} m）
      </label>
    </fieldset>
    <label>砖型 <select v-model.number="tileId"><option v-for="t in tiles" :key="t.id" :value="t.id">{{ t.name }}</option></select></label>
    <label>损耗% <input v-model="wastePct" type="number" min="0" step="0.5" placeholder="留空按设置" /></label>
    <button @click="run(false)">试算</button>
    <button @click="run(true)">保存记录</button>
    <p v-if="err" class="alert">{{ err }}</p>
    <template v-if="result">
      <table class="tbl">
        <thead><tr><th>房间</th><th>面积 m²</th><th>净用量</th><th>损耗%</th><th>下单片数</th><th>铺贴网格</th></tr></thead>
        <tbody>
          <tr v-for="row in result.rooms" :key="row.room_id">
            <td>{{ row.room_name }}</td>
            <td>{{ row.area_m2 }}</td>
            <td>{{ row.raw_count }}</td>
            <td>{{ row.waste_pct }}</td>
            <td>{{ row.order_count }}</td>
            <td>{{ row.layout.cols }}×{{ row.layout.rows }}（{{ row.layout.grid_count }} 格）</td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="total-row">
            <td>合计（{{ result.rooms.length }} 房）</td>
            <td>{{ result.total_area_m2 }}</td>
            <td>{{ result.total_raw_count }}</td>
            <td>{{ result.waste_pct }}</td>
            <td>{{ result.total_order_count }}</td>
            <td></td>
          </tr>
        </tfoot>
      </table>
      <OrderSummary :result="summary" />
      <TileGridPreview
        v-if="result.rooms.length === 1"
        :cols="result.rooms[0].layout.cols"
        :rows="result.rooms[0].layout.rows"
        :grid-count="result.rooms[0].layout.grid_count"
      />
      <p v-if="result.run_id" class="saved">已保存为记录 #{{ result.run_id }}</p>
    </template>
  </div>
</template>
