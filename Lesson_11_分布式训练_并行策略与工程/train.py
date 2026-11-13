from accelerate import Accelerator
from accelerate.utils import DeepSpeedPlugin
import torch
from torch.utils.data import DataLoader, TensorDataset
import torch.nn as nn

# ------------------ 配置 Accelerator 和 Deepspeed ------------------
deep_plugin = DeepSpeedPlugin(zero_stage=2, gradient_clipping=1.0)
accelerator = Accelerator(deepspeed_plugin=deep_plugin)

# ------------------ 简单模型 & 数据 ------------------
class SimpleNet(torch.nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim):
        super(SimpleNet, self).__init__()
        self.fc1 = torch.nn.Linear(input_dim, hidden_dim)  #.to("cuda:0")
        self.fc2 = torch.nn.Linear(hidden_dim, output_dim) #.to("cuda:1")

    def forward(self, x):
        # x.to("cuda:0")
        x = torch.relu(self.fc1(x))
        # x.to("cuda:1")
        x = self.fc2(x)
        return x


if __name__=="__main__":

    input_dim = 10
    hidden_dim = 20
    output_dim = 2
    batch_size = 64
    data_size = 10000

     # ------------------ 初始化模型和数据集 ------------------
    model = SimpleNet(input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()
    
    x = torch.randn(data_size, input_dim)
    y = torch.randn(data_size, output_dim)
    
    dataset = TensorDataset(x, y)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    
    # ------------------ 准备分布式训练 ------------------
    model, dataloader, optimizer = accelerator.prepare(model, dataloader, optimizer)
    
    # ------------------ 简单训练 Loop ------------------
    for epoch in range(1000):
        model.train()
        for batch in dataloader:
            inputs, labels = batch
            outputs = model(inputs)
            loss = loss_fn(outputs, labels)
            
            optimizer.zero_grad()

            #这里不一样
            accelerator.backward(loss)
            optimizer.step()
            
        print(f"Epoch {epoch} loss: {loss.item()}")
            
    
    # ------------------ 保存模型 ------------------
    
    accelerator.save_model(model, "./saved_model")
