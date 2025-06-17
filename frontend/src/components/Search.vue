<template>
  <div class="container">
    <div class="search-header">
      <h2>校园学术讲座信息检索</h2>
      <p class="subtitle">支持中英文混合检索，智能分词，快速定位您感兴趣的讲座信息</p>
    </div>

    <div class="search-box">
      <el-input
        v-model="query"
        :placeholder="placeholder"
        clearable
        @keyup.enter="searchWithSegment"
        class="search-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
        <template #append>
          <el-button type="primary" @click="searchWithSegment" :loading="loading">
            {{ loading ? '搜索中...' : '搜索' }}
          </el-button>
        </template>
      </el-input>
      
      <div class="search-options">
        <el-checkbox v-model="useProximity" label="启用邻近搜索">
          <el-tooltip
            content="邻近搜索会查找词语在文档中距离较近的结果，适合查找短语或相关概念"
            placement="top"
          >
            <span>启用邻近搜索</span>
          </el-tooltip>
        </el-checkbox>
      </div>
    </div>

    <div v-if="segments && segments.length" class="segments">
      <el-tag
        v-for="t in segments"
        :key="t"
        class="tag-term"
        type="info"
        effect="plain"
      >
        {{ t }}
      </el-tag>
    </div>

    <!-- 添加查询纠错建议 -->
    <div v-if="correctedQueries && correctedQueries.length" class="corrected-queries">
      <span class="suggestion-label">您是否想搜索：</span>
      <el-tag
        v-for="q in correctedQueries"
        :key="q"
        class="corrected-query"
        type="warning"
        effect="plain"
        @click="useCorrectedQuery(q)"
      >
        {{ q }}
      </el-tag>
    </div>

    <div class="search-stats">
      <el-tag type="success" effect="plain">
        检索耗时：{{ timeMs }} 毫秒
      </el-tag>
      <el-tag type="info" effect="plain" class="ml-2">
        找到 {{ results.length }} 条结果
      </el-tag>
    </div>

    <div v-if="gptSummary" class="gpt-summary">
      <el-card class="summary-card">
        <template #header>
          <div class="card-header">
            <span>智能总结</span>
            <el-tag size="small" type="success">ChatGLM大模型 生成</el-tag>
          </div>
        </template>
        <div class="summary-content markdown-body" v-html="renderMarkdown(gptSummary)"></div>
      </el-card>
    </div>

    <div v-if="results.length" class="results-container">
      <!-- <el-pagination
        background
        layout="prev, pager, next, sizes"
        :total="results.length"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        class="pagination"
      /> -->

      <div v-for="item in pagedResults" :key="item.doc_id" class="result-item">
        <el-card class="result-card" shadow="hover">
          <div class="result-header">
            <span class="score">相关度：{{ (item.score * 100).toFixed(2) }}%</span>
            <el-link 
              :href="`${backendUrl}/backend/dataset/dataset_html/全部发文单位/${getHtmlPath(item.doc_id)}/index.html`"
              target="_blank"
              type="primary"
              class="read-more"
            >
              阅读全文 <el-icon><ArrowRight /></el-icon>
            </el-link>
          </div>
          <div class="result-content" v-html="highlight(item.snippet, segments)"></div>
        </el-card>
      </div>

      <el-pagination
        background
        layout="prev, pager, next, sizes"
        :total="results.length"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        class="pagination"
      />
    </div>

    <div v-else-if="searched" class="no-results">
      <el-empty description="未找到相关结果" />
    </div>

    <!-- 文档内容对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="currentDoc ? `文档：${currentDoc.doc_id}` : '文档内容'"
      width="70%"
      class="document-dialog"
    >
      <div v-if="currentDoc" class="document-content">
        <div v-html="highlight(currentDoc.content, segments)"></div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search, ArrowRight } from '@element-plus/icons-vue'
import { search, segment } from '../api.js'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import { marked } from 'marked';
import DOMPurify from 'dompurify'

const query = ref('')
const segments = ref([])
const results = ref([])
const timeMs = ref(0)
const gptSummary = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const searched = ref(false)
const backendUrl = 'http://127.0.0.1:5500'
const dialogVisible = ref(false)
const currentDoc = ref(null)
const useProximity = ref(false)  // 是否使用邻近搜索
const correctedQueries = ref([])  // 查询纠错建议

const placeholder = computed(() => {
  return '请输入关键词，例如：人工智能 机器学习 深度学习'
})

const pagedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return results.value.slice(start, start + pageSize.value)
})

// 获取HTML文件路径
function getHtmlPath(docId) {
  // 确保docId是字符串类型
  const docIdStr = String(docId)
  // 从文件名中提取数字（去掉.txt后缀）
  const num = docIdStr.replace('.txt', '')
  // 根据数字范围返回对应的目录号
  const numInt = parseInt(num)
  let dirNum
  if (numInt >= 1000) {
    dirNum = Math.floor((numInt - 1000) / 20) + 1
  } else {
    dirNum = Math.floor(numInt / 20) + 1
  }
  // 将目录号格式化为3位数，不足补0
  return dirNum.toString().padStart(3, '0')
}

async function searchWithSegment() {
  if (!query.value.trim()) {  //输入验证
    ElMessage.warning('请输入搜索关键词')
    return
  }
  //加载状态更新
  loading.value = true
  searched.value = true
  try {  //调用API进行分词（使用大模型）
    const seg = await segment(query.value)
    segments.value = Array.isArray(seg) ? seg : []
    const res = await search(query.value, 50, useProximity.value)  //执行搜索并获取结果
    console.log("后端返回的完整响应：",res);
    timeMs.value = res.elapsed_ms
    console.log("检索耗时:", timeMs.value, "毫秒");
    results.value = res.results
    gptSummary.value = res.gpt_summary || ''   // 从后端响应获取总结
    correctedQueries.value = res.corrected_queries || []  // 获取查询纠错建议
    currentPage.value = 1
  } catch (error) {
    console.error('搜索出错：', error)
    ElMessage.error('搜索失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function highlight(text, terms) {
  if (!text || !terms.length) return text
  const escapedTerms = terms.map(t => t.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&'))
  const regex = new RegExp(`(${escapedTerms.join('|')})`, 'gi')
  return text.replace(regex, '<span class="highlight">$1</span>')
}

async function showDocument(docId) {
  try {
    const response = await axios.get(`${backendUrl}/docs/${docId}`)
    currentDoc.value = response.data
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取文档内容失败')
    console.error('Error fetching document:', error)
  }
}

// 渲染Markdown内容
function renderMarkdown(text) {
  if (!text) return ''
  // 使用marked将Markdown转换为HTML
  const html = marked(text)
  // 使用DOMPurify清理HTML，防止XSS攻击
  return DOMPurify.sanitize(html)
}

// 使用纠错后的查询
function useCorrectedQuery(correctedQuery) {
  query.value = correctedQuery
  searchWithSegment()
}
</script>

<style scoped>
.container {
  max-width: 1000px;
  margin: auto;
  background: #fff;
  padding: 32px;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}

.search-header {
  text-align: center;
  margin-bottom: 32px;
}

.search-header h2 {
  margin: 0;
  color: #2c3e50;
  font-size: 28px;
}

.subtitle {
  color: #666;
  margin-top: 8px;
}

.search-box {
  margin-bottom: 24px;
}

.search-input {
  width: 100%;
}

.search-input :deep(.el-input__wrapper) {
  padding: 8px 16px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.segments {
  margin: 16px 0;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-term {
  margin-right: 8px;
}

.search-stats {
  margin: 16px 0;
  display: flex;
  gap: 12px;
}

.gpt-summary {
  margin: 24px 0;
}

.summary-card {
  background: #f8f9fa;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #ebeef5;
}

.summary-content {
  padding: 20px;
  line-height: 1.6;
  color: #2c3e50;
}

/* Markdown样式 */
:deep(.markdown-body) {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
}

:deep(.markdown-body h2) {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
  padding-bottom: 0.3em;
  border-bottom: 1px solid #eaecef;
  color: #1a1a1a;
}

:deep(.markdown-body ul) {
  padding-left: 2em;
  margin-top: 0;
  margin-bottom: 16px;
}

:deep(.markdown-body li) {
  margin: 0.25em 0;
}

:deep(.markdown-body blockquote) {
  padding: 0 1em;
  color: #6a737d;
  border-left: 0.25em solid #dfe2e5;
  margin: 0 0 16px 0;
}

:deep(.markdown-body strong) {
  font-weight: 600;
  color: #1a1a1a;
}

.results-container {
  margin-top: 24px;
}

.result-item {
  margin-bottom: 16px;
}

.result-card {
  transition: all 0.3s ease;
}

.result-card:hover {
  transform: translateY(-2px);
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.score {
  color: #67c23a;
  font-weight: bold;
}

.read-more {
  display: flex;
  align-items: center;
  gap: 4px;
}

.result-content {
  color: #2c3e50;
  line-height: 1.6;
}

.pagination {
  margin: 24px 0;
  display: flex;
  justify-content: center;
}

.no-results {
  margin: 48px 0;
}

:deep(.highlight) {
  color: #f56c6c;
  font-weight: bold;
  background: #fef0f0;
  padding: 0 2px;
  border-radius: 2px;
}

.ml-2 {
  margin-left: 8px;
}

.document-dialog :deep(.el-dialog__body) {
  max-height: 70vh;
  overflow-y: auto;
}

.document-content {
  white-space: pre-wrap;
  line-height: 1.6;
  font-size: 14px;
  color: #2c3e50;
}

.document-content :deep(.highlight) {
  color: #f56c6c;
  font-weight: bold;
  background: #fef0f0;
  padding: 0 2px;
  border-radius: 2px;
}

.search-options {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.search-options :deep(.el-checkbox__label) {
  font-size: 14px;
  color: #606266;
}

.corrected-queries {
  margin-top: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.suggestion-label {
  font-weight: bold;
  margin-right: 8px;
}

.corrected-query {
  cursor: pointer;
  background-color: #f0f0f0;
  padding: 4px 8px;
  border-radius: 4px;
}
</style>
