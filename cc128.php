<?php
/**
 * add support for marker ...
 * -> in hollyday for example
 * - persist into database
 * -
 */


echo "CC128 PHP parser (".date("d/m/Y H:i").")\n";


/**
 * config section
 */
$nb_sensors = 1; // nb of sensors we want to handle
$nb_frames = 5; // nb of trame to analysis

/**
 * program section
 */

$t_daily_stats = array();
$t_hourly_stats = array();

$now = ''; // TimeStamp at the time we received data
$t_xml = array();


// parsing data from XML ...

$usb = "/dev/ttyUSB0";
$handler = fopen($usb, 'r');
for ($i=0; $i<$nb_frames; $i++) {
	echo "getting data...\n";
	$t_xml[] = fgets($handler);
	//echo fread($handler, 500);
}
fclose($handler);


foreach ($t_xml as $xml) {

	if(strpos($xml, "<") === false) {
		echo "Bad XML : $xml\n";
		continue;
	}

	$o_xml = simplexml_load_string($xml);

	if(! $o_xml) { // xml not valid ...

		continue;
	}

	if($o_xml->sensor) // instantaneous consumption
		echo "at ".$o_xml->time." we were using ".$o_xml->ch1->watts." W\n";
	else { // historical data ...
		echo "Data from last ".$o_xml->hist->dsw." days (current time : ".$o_xml->time."):\n\n";

		// strtotime is magic ;) and for lazy people
		$now = strtotime($o_xml->time); // note that we ignore minutes and seconds
		//echo "TS now : $now\n";

		foreach ($o_xml->hist->data as $data) {

			// we don't mind data for sensors that doesn't exist (first sensor is #0)
			if($data->sensor > $nb_sensors-1) continue;

			echo "Here is sensor #".$data->sensor."\n";
			foreach ($data as $tag => $xdata) {

				if($tag == "sensor") continue;

				// convert tag as date ...
				$precision = substr($tag, 0, 1);
				switch($precision) {

					case "h":
						echo "[".$tag."]".date("d/m/Y H:i", tsFromHTag($tag)) . " : ". $xdata." (".$o_xml->hist->units.")\n";
						$t_hourly_stats[tsFromHTag($tag)] = $xdata;
						break;

					case "d":
						echo "[".$tag."]".date("d/m/Y H:i", tsFromDTag($tag)) . " : ". $xdata." (".$o_xml->hist->units.")\n";
						$t_daily_stats[tsFromDTag($tag)] = $xdata;
						break;

					default:
						echo "Precision $precision isn't handled\n";
						break;
				}


				//echo $tag . " : " . $xdata . "\n";
			}
		}
	}
}


try {
	// store data to sqlite ...
	$db = new PDO('sqlite:cc128.db');

	// does table already exist ?
	$sql = 'CREATE TABLE IF NOT EXISTS consumption (date INTEGER PRIMARY KEY, kwatt REAL) ';
	$db->exec($sql); // remove or 'comment out' this line after first run

	foreach ($t_hourly_stats as $tstamp => $watt) {
		addOrUpdateValue($db, $tstamp, $watt);
	}

	/**
	 * generate data.js ...
	 */
	$t_rows = array();
	foreach ($db->query("select date, kwatt from consumption") as $row) {
		// nomobjet = new Date(annee,mois,jour,heures,minutes,secondes);
		$date = date("Y, n-1, j, G, i, s", $row['date']); // note that month index start at 0 in js
		$t_rows[] = '[new Date('.$date.'), '.$row['kwatt']."]\n";
	}
	$js_rows = implode(',', $t_rows);

	$js =<<<JS
var data = new google.visualization.DataTable();
data.addColumn('datetime', 'Date');
data.addColumn('number', 'KW/h');
data.addRows([
	$js_rows
]);
JS;

	// it's a bit ugly ...
	file_put_contents('data.js', 'var js_exec="'.str_replace("\n", '', $js).'";');

} catch (Exception $e) {
	die($e->getMessage());
}


/**
 *
 * @param unknown_type $db
 * @param unknown_type $tstamp
 * @param unknown_type $kwatt
 */
function addOrUpdateValue($db, $tstamp, $kwatt) {
	$st = $db->prepare('REPLACE INTO consumption (date, kwatt) values (:date, :kwatt)');
	$st->bindParam(':date', $tstamp);
	$st->bindParam(':kwatt', $kwatt);
	$st->execute();
}


function tsFromHTag($htag) {
	global $now;

	$xnow = strtotime(date("H", $now).":00:00"); // note that we ignore minutes and seconds

	$nb = substr($htag, -3);
	//echo "$tag => $nb";
	return strtotime("-$nb hour", $xnow);
}

function tsFromDTag($dtag) {

	$xnow = strtotime("12:00:00"); // at noon...

	$nb = substr($dtag, -3);
	//echo "$tag => $nb";
	return strtotime("-$nb day", $xnow);
}
