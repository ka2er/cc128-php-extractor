var js_exec="var data = new google.visualization.DataTable();data.addColumn('datetime', 'Date');data.addColumn('number', 'KW/h');data.addRows([	[new Date(2010, 3-1, 25, 21, 00, 00), 2.469],[new Date(2010, 3-1, 25, 23, 00, 00), 0.487],[new Date(2010, 3-1, 26, 1, 00, 00), 0.481],[new Date(2010, 3-1, 26, 3, 00, 00), 0.483],[new Date(2010, 3-1, 26, 5, 00, 00), 1.097],[new Date(2010, 3-1, 26, 7, 00, 00), 0.589],[new Date(2010, 3-1, 26, 9, 00, 00), 0.476],[new Date(2010, 3-1, 26, 11, 00, 00), 0.472],[new Date(2010, 3-1, 26, 13, 00, 00), 0.47],[new Date(2010, 3-1, 26, 15, 00, 00), 0.473],[new Date(2010, 3-1, 26, 17, 00, 00), 0.742],[new Date(2010, 3-1, 26, 19, 00, 00), 1.274],[new Date(2010, 3-1, 26, 21, 00, 00), 2.469],[new Date(2010, 3-1, 26, 23, 00, 00), 0.487],[new Date(2010, 3-1, 27, 1, 00, 00), 0.481],[new Date(2010, 3-1, 27, 3, 00, 00), 0.483],[new Date(2010, 3-1, 27, 5, 00, 00), 1.097],[new Date(2010, 3-1, 27, 7, 00, 00), 0.589],[new Date(2010, 3-1, 27, 9, 00, 00), 0.476],[new Date(2010, 3-1, 27, 11, 00, 00), 0.472],[new Date(2010, 3-1, 27, 13, 00, 00), 0.47],[new Date(2010, 3-1, 27, 15, 00, 00), 0.473],[new Date(2010, 3-1, 27, 17, 00, 00), 0.742],[new Date(2010, 3-1, 27, 19, 00, 00), 1.274],[new Date(2010, 3-1, 27, 21, 00, 00), 2.162],[new Date(2010, 3-1, 27, 23, 00, 00), 0.285],[new Date(2010, 3-1, 28, 1, 00, 00), 0.277],[new Date(2010, 3-1, 28, 3, 00, 00), 0.276],[new Date(2010, 3-1, 28, 5, 00, 00), 0.329],[new Date(2010, 3-1, 28, 7, 00, 00), 0.322],[new Date(2010, 3-1, 28, 9, 00, 00), 0.313],[new Date(2010, 3-1, 28, 11, 00, 00), 0.309],[new Date(2010, 3-1, 28, 13, 00, 00), 0.267],[new Date(2010, 3-1, 28, 15, 00, 00), 0.287],[new Date(2010, 3-1, 28, 17, 00, 00), 0.275],[new Date(2010, 3-1, 28, 19, 00, 00), 0.267],[new Date(2010, 3-1, 28, 21, 00, 00), 0.275],[new Date(2010, 3-1, 28, 23, 00, 00), 0.277],[new Date(2010, 3-1, 29, 1, 00, 00), 0.273],[new Date(2010, 3-1, 29, 3, 00, 00), 0.271],[new Date(2010, 3-1, 29, 5, 00, 00), 0.273],[new Date(2010, 3-1, 29, 7, 00, 00), 0.274],[new Date(2010, 3-1, 29, 9, 00, 00), 0.27],[new Date(2010, 3-1, 29, 11, 00, 00), 0.272],[new Date(2010, 3-1, 29, 13, 00, 00), 0.271],[new Date(2010, 3-1, 29, 15, 00, 00), 0.272],[new Date(2010, 3-1, 29, 17, 00, 00), 0.273],[new Date(2010, 3-1, 29, 19, 00, 00), 0.263],[new Date(2010, 3-1, 29, 21, 00, 00), 0.275],[new Date(2010, 3-1, 29, 23, 00, 00), 0.272],[new Date(2010, 3-1, 30, 1, 00, 00), 0.266],[new Date(2010, 3-1, 30, 3, 00, 00), 0.278],[new Date(2010, 3-1, 30, 5, 00, 00), 0.264],[new Date(2010, 3-1, 30, 7, 00, 00), 0.27],[new Date(2010, 3-1, 30, 9, 00, 00), 0.264],[new Date(2010, 3-1, 30, 11, 00, 00), 0.27],[new Date(2010, 3-1, 30, 13, 00, 00), 0.278],[new Date(2010, 3-1, 30, 15, 00, 00), 0.275],[new Date(2010, 3-1, 30, 17, 00, 00), 0.265],[new Date(2010, 3-1, 30, 19, 00, 00), 0.264],[new Date(2010, 3-1, 30, 21, 00, 00), 0.28],[new Date(2010, 3-1, 30, 23, 00, 00), 0.278],[new Date(2010, 3-1, 31, 1, 00, 00), 0.265],[new Date(2010, 3-1, 31, 3, 00, 00), 0.266],[new Date(2010, 3-1, 31, 5, 00, 00), 0.266],[new Date(2010, 3-1, 31, 7, 00, 00), 0.277],[new Date(2010, 3-1, 31, 9, 00, 00), 0.277],[new Date(2010, 3-1, 31, 11, 00, 00), 0.272],[new Date(2010, 3-1, 31, 13, 00, 00), 0.268],[new Date(2010, 3-1, 31, 15, 00, 00), 0.269],[new Date(2010, 3-1, 31, 17, 00, 00), 0.263],[new Date(2010, 3-1, 31, 19, 00, 00), 0.271],[new Date(2010, 3-1, 31, 21, 00, 00), 0.272],[new Date(2010, 3-1, 31, 23, 00, 00), 0.273],[new Date(2010, 4-1, 1, 1, 00, 00), 0.28],[new Date(2010, 4-1, 1, 3, 00, 00), 0.282],[new Date(2010, 4-1, 1, 5, 00, 00), 0.265],[new Date(2010, 4-1, 1, 7, 00, 00), 0.276],[new Date(2010, 4-1, 1, 9, 00, 00), 0.258],[new Date(2010, 4-1, 1, 11, 00, 00), 0.273],[new Date(2010, 4-1, 1, 13, 00, 00), 0.279],[new Date(2010, 4-1, 1, 15, 00, 00), 0.292],[new Date(2010, 4-1, 1, 17, 00, 00), 0.304],[new Date(2010, 4-1, 1, 19, 00, 00), 0.303],[new Date(2010, 4-1, 1, 21, 00, 00), 0.331],[new Date(2010, 4-1, 1, 23, 00, 00), 0.327],[new Date(2010, 4-1, 2, 1, 00, 00), 0.29],[new Date(2010, 4-1, 2, 3, 00, 00), 0.338],[new Date(2010, 4-1, 2, 5, 00, 00), 0.312],[new Date(2010, 4-1, 2, 7, 00, 00), 0.321],[new Date(2010, 4-1, 2, 9, 00, 00), 0.321],[new Date(2010, 4-1, 2, 11, 00, 00), 0.292],[new Date(2010, 4-1, 2, 13, 00, 00), 0.338],[new Date(2010, 4-1, 2, 15, 00, 00), 0.314],[new Date(2010, 4-1, 2, 17, 00, 00), 0.298],[new Date(2010, 4-1, 2, 19, 00, 00), 0.333],[new Date(2010, 4-1, 2, 21, 00, 00), 0.319],[new Date(2010, 4-1, 2, 23, 00, 00), 0.307],[new Date(2010, 4-1, 3, 1, 00, 00), 0.34],[new Date(2010, 4-1, 3, 3, 00, 00), 0.288],[new Date(2010, 4-1, 3, 5, 00, 00), 0.338],[new Date(2010, 4-1, 3, 7, 00, 00), 0.302],[new Date(2010, 4-1, 3, 9, 00, 00), 0.327],[new Date(2010, 4-1, 3, 11, 00, 00), 0.312],[new Date(2010, 4-1, 3, 13, 00, 00), 0.306],[new Date(2010, 4-1, 3, 15, 00, 00), 0.333],[new Date(2010, 4-1, 3, 17, 00, 00), 0.291],[new Date(2010, 4-1, 3, 19, 00, 00), 0.347],[new Date(2010, 4-1, 3, 21, 00, 00), 0.285],[new Date(2010, 4-1, 3, 23, 00, 00), 0.35],[new Date(2010, 4-1, 4, 1, 00, 00), 0.29],[new Date(2010, 4-1, 4, 3, 00, 00), 0.337],[new Date(2010, 4-1, 4, 5, 00, 00), 0.289],[new Date(2010, 4-1, 4, 7, 00, 00), 0.309],[new Date(2010, 4-1, 4, 9, 00, 00), 0.253],[new Date(2010, 4-1, 4, 11, 00, 00), 0.287],[new Date(2010, 4-1, 4, 13, 00, 00), 0.286],[new Date(2010, 4-1, 4, 15, 00, 00), 1.086],[new Date(2010, 4-1, 4, 17, 00, 00), 0.978],[new Date(2010, 4-1, 4, 19, 00, 00), 2.528],[new Date(2010, 4-1, 4, 21, 00, 00), 0.405],[new Date(2010, 4-1, 4, 23, 00, 00), 0.415],[new Date(2010, 4-1, 5, 1, 00, 00), 0.373],[new Date(2010, 4-1, 5, 3, 00, 00), 0.433],[new Date(2010, 4-1, 5, 5, 00, 00), 0.759],[new Date(2010, 4-1, 5, 7, 00, 00), 0.779],[new Date(2010, 4-1, 5, 9, 00, 00), 0.486],[new Date(2010, 4-1, 5, 11, 00, 00), 0.461],[new Date(2010, 4-1, 5, 13, 00, 00), 0.479],[new Date(2010, 4-1, 5, 15, 00, 00), 1.304],[new Date(2010, 4-1, 5, 17, 00, 00), 3.612],[new Date(2010, 4-1, 5, 19, 00, 00), 1.309]]);";