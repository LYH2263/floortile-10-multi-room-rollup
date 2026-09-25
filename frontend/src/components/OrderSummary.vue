<script setup>
defineProps({
  result: { type: Object, default: null },
})
</script>
<template>
  <div v-if="result" class="order-summary">
    <template v-if="result.rooms">
      <div class="hero">{{ result.total.order_count }} 片</div>
      <table class="tbl">
        <thead><tr><th>房间</th><th>尺寸 m</th><th>面积 m²</th><th>净用量</th><th>下单片数</th></tr></thead>
        <tbody>
          <tr v-for="r in result.rooms" :key="r.room_id">
            <td>{{ r.room_name }}</td>
            <td>{{ r.length }}×{{ r.width }}</td>
            <td>{{ r.area_m2 }}</td>
            <td>{{ r.raw_count }}</td>
            <td>{{ r.order_count }}</td>
          </tr>
        </tbody>
      </table>
      <ul>
        <li>合计净用量 {{ result.total.raw_count }} 片，损耗 {{ result.total.waste_pct }}%</li>
        <li>合计地面 {{ result.total.area_m2 }} m²</li>
      </ul>
    </template>
    <template v-else>
      <div class="hero">{{ result.order_count }} 片</div>
      <ul>
        <li>净用量 {{ result.raw_count }} 片，损耗 {{ result.waste_pct }}%</li>
        <li>地面 {{ result.area_m2 }} m²，单砖 {{ result.piece_m2 }} m²</li>
      </ul>
    </template>
  </div>
</template>
