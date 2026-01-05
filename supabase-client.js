// Supabase 客户端初始化
// 使用 config.js 中的配置

let supabaseClient = null;

function initSupabase() {
  if (supabaseClient) {
    return supabaseClient;
  }
  
  // 从 config.js 获取配置
  if (typeof SUPABASE_CONFIG === 'undefined') {
    console.error('SUPABASE_CONFIG is not defined. Please include config.js first.');
    return null;
  }
  
  // 动态加载 Supabase JS SDK（如果还没有加载）
  if (typeof supabase === 'undefined') {
    console.error('Supabase JS SDK is not loaded. Please include the Supabase CDN script.');
    return null;
  }
  
  // 初始化 Supabase 客户端
  supabaseClient = supabase.createClient(
    SUPABASE_CONFIG.URL,
    SUPABASE_CONFIG.ANON_KEY
  );
  
  return supabaseClient;
}

// 自动初始化
if (typeof SUPABASE_CONFIG !== 'undefined' && typeof supabase !== 'undefined') {
  initSupabase();
}
