import matplotlib.pyplot as plt

class DataLogger:
    def __init__(self):
        self.data = {}
    
    def log(self, **kwargs):
        """
        Log any number of variables provided as keyword arguments.
        """
        for key, value in kwargs.items():
            if key not in self.data:
                self.data[key] = []
            self.data[key].append(value)
    
    def plot(self, x_key='time', y_keys=None):
        """
        Plot the logged data.
        :param x_key: The key to use for the x-axis (default is 'time').
        :param y_keys: A list of keys to plot against x_key. If None, all keys except x_key are plotted.
        """
        if y_keys is None:
            y_keys = [key for key in self.data.keys() if key != x_key]
        
        for y_key in y_keys:
            plt.figure()
            plt.plot(self.data[x_key], self.data[y_key], label=y_key)
            plt.xlabel(x_key)
            plt.ylabel(y_key)
            plt.title(f'{y_key} vs {x_key}')
            plt.legend()
            plt.show() 
            
        self.save_plot()

    def save_plot(self, x_key='time'):
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        axes = axes.flatten()
        y_keys = [key for key in self.data.keys() if key != x_key]

        plot_labels = [
            {"title": "Position", "xlabel": "Time (s)", "ylabel": "Position (m)"},
            {"title": "Velocity", "xlabel": "Time (s)", "ylabel": "Velocity (m/s)"},
            {"title": "Pitch", "xlabel": "Time (s)", "ylabel": "Pitch (deg)"},
            {"title": "Pitch Rate", "xlabel": "Time (s)", "ylabel": "Pitch Rate (rad/s)"},
            {"title": "Yaw", "xlabel": "Time (s)", "ylabel": "Yaw (rad)"},
            {"title": "Yaw Rate", "xlabel": "Time (s)", "ylabel": "Yaw Rate (rad/s)"}
        ]


        for i in range(0, len(y_keys), 2):
            ax = axes[i // 2]
            ax.plot(self.data[x_key], self.data[y_keys[i]])
            ax.plot(self.data[x_key], self.data[y_keys[i+1]])
            ax.set_xlabel(plot_labels[i//2]["xlabel"])
            ax.set_ylabel(plot_labels[i//2]["ylabel"])
            ax.set_title(plot_labels[i//2]["title"])
            ax.legend(["Position", "Desired Position"])
            ax.grid(True)

        plt.tight_layout()
        plt.savefig('plot.png')