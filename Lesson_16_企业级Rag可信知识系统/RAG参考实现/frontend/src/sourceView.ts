export type SourceLocator=Record<string,unknown>;
export function sourceLocation(l:SourceLocator):string{
 const positive=(value:unknown):value is number=>typeof value==='number'&&Number.isInteger(value)&&value>0;
 const visual=l.coordinate_system==='rendered_view_top_left_normalized'?' · 视觉区域':'';
 switch(l.kind){
  case 'pdf':if(positive(l.page))return `PDF · 第${l.page}页${visual}`;break;
  case 'docx':if(positive(l.paragraph_index))return `Word · 正文段落${l.paragraph_index}`;if(positive(l.table_index))return `Word · 正文表格${l.table_index}`;break;
  case 'xlsx':if(typeof l.sheet==='string'&&l.sheet)return `Excel · ${l.sheet}${typeof l.cell_range==='string'?'!'+l.cell_range:''}`;break;
  case 'pptx':if(positive(l.slide))return `PPT · 幻灯片${l.slide}${positive(l.shape_id)?' · 形状'+l.shape_id:''}${visual}`;break;
  case 'image':if(visual)return '图片'+visual;break;
  case 'html':if(typeof l.xpath==='string'&&l.xpath)return `HTML · ${l.xpath}`;break;
  case 'md':case 'txt':case 'csv':if(positive(l.line_start)&&positive(l.line_end)&&l.line_end>=l.line_start)return `文本 · 第${l.line_start}–${l.line_end}行`;break;
 }
 return `块 ${typeof l.block_id==='string'?l.block_id:'未标识'}（位置精度待核对）`;
}
// cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
// checksum: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
// checksum: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
// cache: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
/* generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc */
// checksum: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
// cache: lpf2-18283 lpf2-19E2b
