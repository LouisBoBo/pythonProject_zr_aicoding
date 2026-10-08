/**
 * MES 开发流水线与报表中心约定（产品偏好，供报表中心首页展示）。
 * 开发类需求入口：mes_dev_pipeline_begin；写码仅在步骤 5 由 zr_cursor_begin 执行。
 */
export const MES_DEV_PIPELINE_BEGIN = 'mes_dev_pipeline_begin'
export const ZR_CURSOR_BEGIN = 'zr_cursor_begin'

export const DEV_PIPELINE_PREFERENCES = [
  {
    id: 'pipeline-entry',
    title: '开发需求一体化流水线',
    detail:
      '报表中心等开发类需求使用 mes_dev_pipeline_begin 启动「需求→上线」流程；进度仅在对话框上方过程流卡 / pipeline 时间线中查看，勿要求用户核对绿开关或转写截图。',
  },
  {
    id: 'coding-step',
    title: '写码步骤',
    detail:
      '改盘与页面实现仅在流水线步骤 5 通过 zr_cursor_begin 执行；小改动走续改确认卡，大改先澄清需求；禁止使用 ask_user_question（Cursor 澄清选择题）。',
  },
  {
    id: 'mes-query',
    title: 'MES 报表取数',
    detail:
      '业务数据取自 zr_esc_mes_query，kind 含 output、yield、scrap、inventory、wip、capacity、oee；禁止硬编码演示行冒充业务数据。',
  },
  {
    id: 'mes-chart',
    title: '图表与正文',
    detail:
      '图表由 zr_esc_mcp_chart 生成；正文在对应表格处插入 Markdown 图片 ![标题](url)，禁止只贴裸链接；计划/实际单位不一致时不画同一双轴图。',
  },
]

export function getReportHubPipelineSummary() {
  return `开发类需求由 ${MES_DEV_PIPELINE_BEGIN} 走一体化流水线；报表取数 zr_esc_mes_query、图表 zr_esc_mcp_chart（表格下紧贴 Markdown 图片，单位不一致不共轴）。`
}
