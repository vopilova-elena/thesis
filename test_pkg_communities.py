import matplotlib.pyplot as plt
import networkx as nx
from networkx.algorithms.community.centrality import girvan_newman
import seaborn as sns


# Create a graph(e.g., social network)
G = nx.karate_club_graph()

# Detect communities using Girvan - Newman algorithm
communities = girvan_newman(G)


# Extract communities from the iterator
node_groups = [list(com) for com in next(communities)]

palette = sns.color_palette('rocket', len(node_groups)) # Default color palette

#colors = Spectral[len(node_groups)]
# Plot the graph with nodes colored by community
color_map = []
for node in G:
    if node in node_groups[0]:
        color_map.append(palette[0])
    else:
        color_map.append(palette[1])

nx.draw(G, node_color = color_map, with_labels = True)
plt.show()

# Output the detected communities
print("Detected Communities:", node_groups)
