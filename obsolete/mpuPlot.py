# import matplotlib.pyplot as plt
# import numpy as np

# class mpuPlot:
#     def __init__(self):
#         self.ag = np.empty([0,6])
#         self.ag_name = ['ax','ay','az','gx','gy','gz']
#         plt.ion()  # Turn on interactive mode
#         self.fig = plt.figure(figsize=(10, 6))  # Set figure size
        
#     def add_data(self, mot):
#         # Check if window was closed
#         if not plt.get_fignums():
#             return False
            
#         self.ag = np.vstack((self.ag, mot))
#         plt.clf()
#         for i in range(6):
#             plt.plot(self.ag[:,i], label=self.ag_name[i])
#         plt.legend()
#         plt.grid(True)
#         plt.pause(0.05)  # Small pause to update the plot
#         return True
        
#     def close(self):
#         plt.close()