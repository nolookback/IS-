import axios from 'axios'

const BASE = 'http://127.0.0.1:5000'  // 后端 Flask 服务地址

export async function search(query, topk = 10, use_proximity = false) {
  const res = await axios.post(`${BASE}/api/search`, { 
    query, 
    topk,
    use_proximity 
  })
  return res.data
}

export async function segment(text) {
  const res = await axios.post(`${BASE}/segment`, { text })
  return res.data.tokens
}
