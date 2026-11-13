import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端

import matplotlib.pyplot as plt
import numpy as np
import uuid
import time
import logging
import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
import sys
sys.path.append('/app/shared')

from app.models.viz_models import GenerateRequest
from app.core.config import settings

logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Noto Sans CJK JP', 'Noto Sans CJK SC', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class VisualizationEngine:
    """可视化引擎"""
    
    def __init__(self):
        self.static_path = Path(settings.STATIC_FILES_PATH)
        self.images_path = self.static_path / "images"
        self.images_path.mkdir(parents=True, exist_ok=True)
        
        # 图片生成统计
        self.stats = {
            "total_generated": 0,
            "success_count": 0,
            "error_count": 0
        }
    
    async def generate_visualization(self, request: GenerateRequest) -> Optional[Dict[str, Any]]:
        """生成可视化图片"""
        start_time = time.time()
        
        try:
            self.stats["total_generated"] += 1
            
            # 生成唯一ID
            image_id = str(uuid.uuid4())
            image_filename = f"{image_id}.png"
            image_path = self.images_path / image_filename
            
            # 分析问题类型并生成对应的图形
            success = await self._generate_math_plot(request, image_path)
            
            if success:
                self.stats["success_count"] += 1
                generation_time = time.time() - start_time
                
                # 构建访问URL
                image_url = f"/static/images/{image_filename}"
                
                return {
                    "image_id": image_id,
                    "image_url": image_url,
                    "local_path": str(image_path),
                    "generation_time": generation_time
                }
            else:
                self.stats["error_count"] += 1
                return None
                
        except Exception as e:
            self.stats["error_count"] += 1
            logger.error(f"Error generating visualization: {e}")
            return None
    
    async def _generate_math_plot(self, request: GenerateRequest, image_path: Path) -> bool:
        """生成数学图形"""
        try:
            # 在线程池中执行matplotlib操作，避免阻塞
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, 
                self._create_math_plot, 
                request, 
                image_path
            )
        except Exception as e:
            logger.error(f"Error in math plot generation: {e}")
            return False
    
    def _create_math_plot(self, request: GenerateRequest, image_path: Path) -> bool:
        """创建数学图形（同步方法）"""
        try:
            # 分析问题类型
            plot_type = self._analyze_plot_type(request.text, request.answer_text)
            
            # 创建图形
            fig, ax = plt.subplots(figsize=(10, 8))
            
            if plot_type == "function":
                self._create_function_plot(ax, request)
            elif plot_type == "geometry":
                self._create_geometry_plot(ax, request)
            elif plot_type == "coordinate":
                self._create_coordinate_plot(ax, request)
            else:
                # 默认创建一个示例图形
                self._create_default_plot(ax, request)
            
            # 设置图形属性
            ax.grid(True, alpha=0.3)
            ax.set_aspect('equal', adjustable='box')
            
            # 添加标题
            title = self._generate_title(request)
            plt.title(title, fontsize=14, pad=20)
            
            # 保存图片
            plt.savefig(
                image_path, 
                dpi=150, 
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none'
            )
            plt.close(fig)  # 释放内存
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating math plot: {e}")
            return False
    
    def _analyze_plot_type(self, text: str, answer_text: str) -> str:
        """分析图形类型"""
        combined_text = (text + " " + answer_text).lower()
        
        # 函数图像
        if any(keyword in combined_text for keyword in ["函数", "y=", "f(x)", "图像", "曲线"]):
            return "function"
        
        # 几何图形
        if any(keyword in combined_text for keyword in ["三角形", "圆", "正方形", "长方形", "几何"]):
            return "geometry"
        
        # 坐标系
        if any(keyword in combined_text for keyword in ["坐标", "点", "直线", "解析几何"]):
            return "coordinate"
        
        return "default"
    
    def _create_function_plot(self, ax, request: GenerateRequest):
        """创建函数图像"""
        # 示例：创建一个二次函数图像
        x = np.linspace(-5, 5, 100)
        
        # 尝试从文本中提取函数
        if "x²" in request.text or "x^2" in request.text:
            y = x**2
            ax.plot(x, y, 'b-', linewidth=2, label='y = x²')
        elif "sin" in request.text.lower():
            y = np.sin(x)
            ax.plot(x, y, 'r-', linewidth=2, label='y = sin(x)')
        elif "cos" in request.text.lower():
            y = np.cos(x)
            ax.plot(x, y, 'g-', linewidth=2, label='y = cos(x)')
        else:
            # 默认线性函数
            y = 2*x + 1
            ax.plot(x, y, 'b-', linewidth=2, label='y = 2x + 1')
        
        ax.axhline(y=0, color='k', linewidth=0.5)
        ax.axvline(x=0, color='k', linewidth=0.5)
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.legend()
        ax.grid(True)
    
    def _create_geometry_plot(self, ax, request: GenerateRequest):
        """创建几何图形"""
        if "圆" in request.text:
            # 画圆
            circle = plt.Circle((0, 0), 2, fill=False, color='blue', linewidth=2)
            ax.add_patch(circle)
            ax.set_xlim(-3, 3)
            ax.set_ylim(-3, 3)
            
            # 标注圆心
            ax.plot(0, 0, 'ro', markersize=5)
            ax.annotate('O(0,0)', xy=(0, 0), xytext=(0.3, 0.3))
            
        elif "三角形" in request.text:
            # 画三角形
            triangle_x = [0, 3, 1.5, 0]
            triangle_y = [0, 0, 2.6, 0]
            ax.plot(triangle_x, triangle_y, 'b-', linewidth=2)
            
            # 标注顶点
            ax.plot([0, 3, 1.5], [0, 0, 2.6], 'ro', markersize=5)
            ax.annotate('A', xy=(0, 0), xytext=(-0.2, -0.2))
            ax.annotate('B', xy=(3, 0), xytext=(3.1, -0.2))
            ax.annotate('C', xy=(1.5, 2.6), xytext=(1.6, 2.7))
            
            ax.set_xlim(-1, 4)
            ax.set_ylim(-1, 3)
            
        else:
            # 默认正方形
            square_x = [0, 2, 2, 0, 0]
            square_y = [0, 0, 2, 2, 0]
            ax.plot(square_x, square_y, 'g-', linewidth=2)
            ax.set_xlim(-1, 3)
            ax.set_ylim(-1, 3)
    
    def _create_coordinate_plot(self, ax, request: GenerateRequest):
        """创建坐标系图形"""
        # 创建坐标系
        ax.axhline(y=0, color='k', linewidth=1)
        ax.axvline(x=0, color='k', linewidth=1)
        
        # 添加一些示例点
        points_x = [1, 2, -1, -2]
        points_y = [2, -1, 1, -2]
        ax.scatter(points_x, points_y, c='red', s=50)
        
        # 标注点
        for i, (x, y) in enumerate(zip(points_x, points_y)):
            ax.annotate(f'P{i+1}({x},{y})', xy=(x, y), xytext=(x+0.2, y+0.2))
        
        ax.set_xlim(-3, 3)
        ax.set_ylim(-3, 3)
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.grid(True)
    
    def _create_default_plot(self, ax, request: GenerateRequest):
        """创建默认图形"""
        # 创建一个简单的数学示例图
        x = np.linspace(0, 2*np.pi, 100)
        y1 = np.sin(x)
        y2 = np.cos(x)
        
        ax.plot(x, y1, 'b-', label='sin(x)', linewidth=2)
        ax.plot(x, y2, 'r-', label='cos(x)', linewidth=2)
        
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.legend()
        ax.grid(True)
    
    def _generate_title(self, request: GenerateRequest) -> str:
        """生成图形标题"""
        if "函数" in request.text:
            return "函数图像"
        elif "几何" in request.text or "三角形" in request.text or "圆" in request.text:
            return "几何图形"
        elif "坐标" in request.text:
            return "坐标系图形"
        else:
            return "数学图形"
    
    def get_image_path(self, image_id: str) -> Optional[Path]:
        """获取图片路径"""
        image_path = self.images_path / f"{image_id}.png"
        return image_path if image_path.exists() else None
    
    async def get_image_info(self, image_id: str) -> Optional[Dict[str, Any]]:
        """获取图片信息"""
        image_path = self.get_image_path(image_id)
        
        if image_path:
            stat = image_path.stat()
            return {
                "image_id": image_id,
                "filename": image_path.name,
                "size": stat.st_size,
                "created_time": stat.st_ctime,
                "url": f"/static/images/{image_path.name}"
            }
        
        return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            "images_directory": str(self.images_path),
            "total_images": len(list(self.images_path.glob("*.png")))
        } 