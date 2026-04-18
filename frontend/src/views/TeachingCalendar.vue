<template>
  <div class="calendar-container">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>📅 教学日历</span>
          <div class="month-nav">
            <el-button :icon="ArrowLeft" circle size="small" @click="prevMonth" />
            <span class="month-label">{{ year }}年{{ month }}月</span>
            <el-button :icon="ArrowRight" circle size="small" @click="nextMonth" />
            <el-button size="small" style="margin-left: 8px" @click="goToday">今天</el-button>
          </div>
        </div>
      </template>

      <div v-loading="loading" class="calendar-grid">
        <!-- 星期表头 -->
        <div class="weekday-header">
          <div v-for="wd in weekdays" :key="wd" class="weekday-cell">{{ wd }}</div>
        </div>

        <!-- 日期格子 -->
        <div class="day-grid">
          <div
            v-for="(cell, idx) in calendarCells"
            :key="idx"
            :class="['day-cell', {
              'other-month': !cell.currentMonth,
              'is-today': cell.isToday,
              'has-events': cell.events.length > 0,
            }]"
          >
            <div class="day-number">{{ cell.day }}</div>
            <div class="events-list">
              <div
                v-for="ev in cell.events"
                :key="ev.schedule_id"
                :class="['event-item', { 'event-holiday': ev.is_holiday }]"
                @click="goToSchedule(ev)"
              >
                <el-tooltip
                  :content="`${ev.course_name} | ${ev.class_name} | ${ev.start_time}-${ev.end_time} | ${ev.location || '无教室'}${ev.is_holiday ? ' (节假日停课: ' + ev.holiday_name + ')' : ''}`"
                  placement="top"
                >
                  <span class="event-text">
                    <span v-if="ev.is_holiday" class="holiday-tag">休</span>
                    {{ ev.start_time }} {{ ev.course_name }}
                  </span>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import request from '../utils/request'

interface CalendarEvent {
  schedule_id: number
  course_name: string
  class_name: string
  start_time: string
  end_time: string
  location: string | null
  is_holiday: boolean
  holiday_name: string | null
}

interface CalendarDay {
  date: string
  events: CalendarEvent[]
}

interface CellData {
  day: number
  fullDate: string
  currentMonth: boolean
  isToday: boolean
  events: CalendarEvent[]
}

const router = useRouter()
const today = new Date()
const year = ref(today.getFullYear())
const month = ref(today.getMonth() + 1) // 1-12
const loading = ref(false)
const weekdays = ['一', '二', '三', '四', '五', '六', '日']

// 按日期索引事件 { "2026-04-20": [...events] }
const eventsMap = ref<Record<string, CalendarEvent[]>>({})

const role = localStorage.getItem('role') || ''

async function fetchCalendar() {
  loading.value = true
  try {
    const { data } = await request.get('/api/v1/calendar', {
      params: { year: year.value, month: month.value },
    })
    const map: Record<string, CalendarEvent[]> = {}
    for (const d of data as CalendarDay[]) {
      map[d.date] = d.events
    }
    eventsMap.value = map
  } catch {
    eventsMap.value = {}
  } finally {
    loading.value = false
  }
}

// 计算日历 6 行 × 7 列
const calendarCells = computed<CellData[]>(() => {
  const cells: CellData[] = []
  const firstDay = new Date(year.value, month.value - 1, 1)
  // 一周从周一开始，getDay(): 0=Sun -> adjust
  let startOffset = firstDay.getDay() - 1
  if (startOffset < 0) startOffset = 6 // Sunday

  const daysInMonth = new Date(year.value, month.value, 0).getDate()
  const prevMonthDays = new Date(year.value, month.value - 1, 0).getDate()

  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

  // 上月填充
  for (let i = startOffset - 1; i >= 0; i--) {
    const d = prevMonthDays - i
    const m = month.value - 1 <= 0 ? 12 : month.value - 1
    const y = month.value - 1 <= 0 ? year.value - 1 : year.value
    const fullDate = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, fullDate, currentMonth: false, isToday: fullDate === todayStr, events: [] })
  }

  // 当月
  for (let d = 1; d <= daysInMonth; d++) {
    const fullDate = `${year.value}-${String(month.value).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({
      day: d,
      fullDate,
      currentMonth: true,
      isToday: fullDate === todayStr,
      events: eventsMap.value[fullDate] || [],
    })
  }

  // 下月填充到 42 格
  const remaining = 42 - cells.length
  for (let d = 1; d <= remaining; d++) {
    const m = month.value + 1 > 12 ? 1 : month.value + 1
    const y = month.value + 1 > 12 ? year.value + 1 : year.value
    const fullDate = `${y}-${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({ day: d, fullDate, currentMonth: false, isToday: fullDate === todayStr, events: [] })
  }

  return cells
})

function prevMonth() {
  if (month.value === 1) { year.value--; month.value = 12 }
  else month.value--
}

function nextMonth() {
  if (month.value === 12) { year.value++; month.value = 1 }
  else month.value++
}

function goToday() {
  year.value = today.getFullYear()
  month.value = today.getMonth() + 1
}

function goToSchedule(ev: CalendarEvent) {
  if (ev.is_holiday) return
  if (role === 'teacher') {
    router.push('/courses')
  } else if (role === 'student') {
    router.push({ path: '/check_in', query: { schedule_id: ev.schedule_id } })
  }
}

watch([year, month], () => fetchCalendar())
onMounted(() => fetchCalendar())
</script>

<style scoped>
.calendar-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 600;
}

.month-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.month-label {
  font-size: 16px;
  font-weight: 600;
  min-width: 100px;
  text-align: center;
}

.weekday-header {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-weight: 600;
  color: #606266;
  border-bottom: 1px solid #ebeef5;
  padding: 8px 0;
}

.weekday-cell {
  padding: 6px;
}

.day-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background-color: #ebeef5;
}

.day-cell {
  background: #fff;
  min-height: 100px;
  padding: 4px 6px;
  position: relative;
  transition: background 0.2s;
}

.day-cell:hover {
  background: #f5f7fa;
}

.day-cell.other-month {
  background: #fafafa;
}

.day-cell.other-month .day-number {
  color: #c0c4cc;
}

.day-cell.is-today .day-number {
  background-color: #409eff;
  color: #fff;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  line-height: 24px;
  text-align: center;
  display: inline-block;
}

.day-number {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.event-item {
  padding: 2px 4px;
  border-radius: 3px;
  background-color: #ecf5ff;
  border-left: 3px solid #409eff;
  cursor: pointer;
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  transition: all 0.2s;
}

.event-item:hover {
  background-color: #d9ecff;
}

.event-item.event-holiday {
  background-color: #fef0f0;
  border-left-color: #f56c6c;
  text-decoration: line-through;
  cursor: default;
  opacity: 0.7;
}

.event-text {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.holiday-tag {
  display: inline-block;
  background-color: #f56c6c;
  color: #fff;
  font-size: 10px;
  width: 16px;
  height: 16px;
  line-height: 16px;
  text-align: center;
  border-radius: 3px;
  flex-shrink: 0;
}
</style>
