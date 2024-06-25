from pyvis.network import Network

net = Network()  # создаём объект графа

# добавление узлов
net.add_nodes(
    [1, 2, 3, 4, 5],  # node ids
    label=['Node #1', 'Node #2', 'Node #3', 'Node #4', 'Node #5'],  # node labels
    # node titles (display on mouse hover)
    title=['Main node', 'Just node', 'Just node', 'Just node', 'Node with self-loop'],
    color=['#d47415', '#22b512', '#42adf5', '#4a21b0', '#e627a3']  # node colors (HEX)
)
# добавляем тот же список узлов, что и в предыдущем примере
net.add_edges([(1, 2), (1, 3), (2, 3), (2, 4), (3, 5), (5, 5)])

net.show('graph.html', notebook=False)  # save visualization in 'graph.html'