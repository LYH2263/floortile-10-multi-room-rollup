<script setup>
import { onMounted, ref } from 'vue'
import { getJSON } from '../api'
const items = ref([])
const openId = ref(null)
onMounted(async () => { items.value = (await getJSON('/api/runs')).items })
const isBatch = r => Array.isArray(r.result?.rooms)
const roomCell = r => isBatch(r) ? `合并 ${r.result.rooms.length} 房` : r.room_name
const countCell = r => isBatch(r) ? r.result.total?.order_count : r.result?.order_count
function toggle(id) { openId.value = openId.value === id ? null : id }
</script>
<template>
  <div class="page">
    <h1>测算记录</h1>
    <table class="tbl">
      <thead><tr><th>时间</th><th>房间</th><th>砖型</th><th>片数</th></tr></thead>
      <tbody>
        <template v-for="r in items" :key="r.id">
          <tr class="run-row" @click="toggle(r.id)">
            <td>{{ r.created_at?.slice(0, 19) }}</td>
            <td>{{ roomCell(r) }}</td>
            <td>{{ r.tile_name }}</td>
            <td>{{ countCell(r) }}</td>
          </tr>
          <tr v-if="openId === r.id" class="run-detail">
            <td colspan="4">
              <table v-if="isBatch(r)" class="tbl">
                <thead><tr><th>房间</th><th>尺寸 m</th><th>净用量</th><th>下单片数</th></tr></thead>
                <tbody>
                  <tr v-for="room in r.result.rooms" :key="room.room_id">
                    <td>{{ room.room_name }}</td>
                    <td>{{ room.length }}×{{ room.width }}</td>
                    <td>{{ room.raw_count }}</td>
                    <td>{{ room.order_count }}</td>
                  </tr>
                  <tr>
                    <td><strong>合计</strong></td>
                    <td>—</td>
                    <td><strong>{{ r.result.total.raw_count }}</strong></td>
                    <td><strong>{{ r.result.total.order_count }}</strong></td>
                  </tr>
                </tbody>
              </table>
              <p v-else>净用量 {{ r.result?.raw_count }} 片，损耗 {{ r.result?.waste_pct }}%<template v-if="r.note">；备注：{{ r.note }}</template></p>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
</template>
