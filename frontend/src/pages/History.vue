<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'

const items = ref([])
const openId = ref(null)
const detail = ref(null)

onMounted(async () => { items.value = (await getJSON('/api/runs')).items })

const isBatch = r => Array.isArray(r.result?.rooms)
const roomLabel = r => (isBatch(r) ? `合并（${r.result.rooms.length} 房）` : r.room_name)
const orderCount = r => r.result?.total_order_count ?? r.result?.order_count

async function toggle(r) {
  if (openId.value === r.id) {
    openId.value = null
    detail.value = null
    return
  }
  openId.value = r.id
  detail.value = await getJSON(`/api/runs/${r.id}`)
}
</script>
<template>
  <div class="page">
    <h1>测算记录</h1>
    <table class="tbl">
      <thead><tr><th>时间</th><th>房间</th><th>砖型</th><th>片数</th></tr></thead>
      <tbody>
        <template v-for="r in items" :key="r.id">
          <tr class="clickable" :class="{ open: openId === r.id }" @click="toggle(r)">
            <td>{{ r.created_at?.slice(0, 19) }}</td>
            <td>{{ roomLabel(r) }}</td>
            <td>{{ r.tile_name }}</td>
            <td>{{ orderCount(r) }}</td>
          </tr>
          <tr v-if="openId === r.id && detail" class="run-detail">
            <td colspan="4">
              <template v-if="isBatch(detail)">
                <table class="tbl">
                  <thead><tr><th>房间</th><th>面积 m²</th><th>净用量</th><th>损耗%</th><th>下单片数</th></tr></thead>
                  <tbody>
                    <tr v-for="row in detail.result.rooms" :key="row.room_id">
                      <td>{{ row.room_name }}</td>
                      <td>{{ row.area_m2 }}</td>
                      <td>{{ row.raw_count }}</td>
                      <td>{{ row.waste_pct }}</td>
                      <td>{{ row.order_count }}</td>
                    </tr>
                  </tbody>
                  <tfoot>
                    <tr class="total-row">
                      <td>合计</td>
                      <td>{{ detail.result.total_area_m2 }}</td>
                      <td>{{ detail.result.total_raw_count }}</td>
                      <td>{{ detail.result.waste_pct }}</td>
                      <td>{{ detail.result.total_order_count }}</td>
                    </tr>
                  </tfoot>
                </table>
              </template>
              <template v-else>
                净用量 {{ detail.result.raw_count }} 片，损耗 {{ detail.result.waste_pct }}%，地面 {{ detail.result.area_m2 }} m²
                <span v-if="detail.note">；备注：{{ detail.note }}</span>
              </template>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>
