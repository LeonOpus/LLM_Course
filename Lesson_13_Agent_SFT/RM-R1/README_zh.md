# RM-R1：训练流程
RM‑R1 将奖励建模问题重构为一个“推理”问题。与其直接输出一个不可解释的标量分数，Reasoning Reward Model（ReasRM）首先“逐步思考”——生成结构化的评分标准或解题思路——随后再预测两条回答的偏好。这一简单转变同时提升了“可解释性”与“效果”：RM‑R1 在多个公开基准上平均超过以往的 SOTA 奖励模型，并且可以让你直观看到模型为何偏好某个答案。

## 1. 基础环境
conda create -n rm-r1-1 python=3.11 -y
conda activate rm-r1-1

## 2. veRL（固定提交）
git clone https://github.com/volcengine/verl
cd verl
git checkout e49fb572bf85a8f0ef7124c898f509bd6d9832a1
pip install -e .

## 3. vLLM（固定提交 + flash‑attention）
git clone https://github.com/vllm-project/vllm.git
cd vllm
git checkout ed6e9075d31e32c8548b480a47d1ffb77da1f54c
git config --global user.name "你的名字"
git config --global user.email "你的邮箱地址@example.com"
git cherry-pick caac5c2e597b1780c3df54a537c34e6061c32cff
export VLLM_COMMIT=ed6e9075d31e32c8548b480a47d1ffb77da1f54c
export VLLM_PRECOMPILED_WHEEL_LOCATION=https://wheels.vllm.ai/ed6e9075d31e32c8548b480a47d1ffb77da1f54c/vllm-1.0.0.dev-cp38-abi3-manylinux1_x86_64.whl
VLLM_USE_PRECOMPILED=1 pip install --editable .

### flash‑attention 2（>2× 加速）
pip install flash-attn==2.7.2.post1 --no-build-isolation

完成！ 现在可以开始进行 RM‑R1 的 RL 训练。


## 4. 训练流程（Training Workflow）
训练配方位于 rm_r1/scripts/，跳过SFT，直接对推理模型进行GRPO训练：
🔧 示例：微调一个 DeepSeek 蒸馏的检查点
cd /root/autodl-tmp/RM-R1
bash ./rm_r1/scripts/RLVR/local/train_rm_r1_rlvr_dpsk_distilled_7b.sh