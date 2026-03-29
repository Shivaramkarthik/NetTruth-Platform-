"""Unified prediction engine combining all ML models."""
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from app.ml.anomaly_detector import AnomalyDetector
from app.ml.throttling_classifier import ThrottlingClassifier
from app.ml.time_series_analyzer import TimeSeriesAnalyzer


class PredictionEngine:
    """
    Unified prediction engine that combines all ML models
    for comprehensive throttling detection and analysis.
    """
    
    def __init__(self):
        """Initialize all ML models."""
        self.anomaly_detector = AnomalyDetector()
        self.throttling_classifier = ThrottlingClassifier()
        self.time_series_analyzer = TimeSeriesAnalyzer()
        
        logger.info("Prediction engine initialized with all models")
    
    def analyze(self, data: List[Dict], include_predictions: bool = True) -> Dict:
        """
        Perform comprehensive analysis on network data.
        
        Args:
            data: List of network log dictionaries
            include_predictions: Whether to include future predictions
            
        Returns:
            Comprehensive analysis results
        """
        if not data:
            return {"error": "No data provided"}
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "data_points_analyzed": len(data),
            "anomaly_detection": {},
            "throttling_classification": {},
            "time_series_analysis": {},
            "summary": {},
            "alerts": []
        }
        
        # Step 1: Anomaly Detection
        try:
            anomaly_results = self.anomaly_detector.detect(data)
            anomalies = [r for r in anomaly_results if r.get('is_anomaly')]
            
            results["anomaly_detection"] = {
                "total_anomalies": len(anomalies),
                "anomaly_rate": len(anomalies) / len(data) if data else 0,
                "anomalies": anomalies[:10]  # Top 10 anomalies
            }
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            results["anomaly_detection"] = {"error": str(e)}
        
        # Step 2: Throttling Classification (for anomalies)
        try:
            if anomalies:
                # Get the data points that were flagged as anomalies
                anomaly_indices = [a['index'] for a in anomalies]
                anomaly_data = [data[i] for i in anomaly_indices if i < len(data)]
                
                classification_results = self.throttling_classifier.classify(anomaly_data)
                
                # Count throttling types
                throttling_counts = {}
                for result in classification_results:
                    t_type = result.get('throttling_type', 'unknown')
                    throttling_counts[t_type] = throttling_counts.get(t_type, 0) + 1
                
                # Get high-confidence throttling events
                confirmed_throttling = [
                    r for r in classification_results
                    if r.get('is_throttling') and r.get('confidence', 0) > 0.7
                ]
                
                results["throttling_classification"] = {
                    "throttling_events": len(confirmed_throttling),
                    "throttling_types": throttling_counts,
                    "high_confidence_events": confirmed_throttling[:10]
                }
            else:
                results["throttling_classification"] = {
                    "throttling_events": 0,
                    "message": "No anomalies detected to classify"
                }
        except Exception as e:
            logger.error(f"Throttling classification error: {e}")
            results["throttling_classification"] = {"error": str(e)}
        
        # Step 3: Time Series Analysis
        try:
            pattern_analysis = self.time_series_analyzer.analyze_patterns(data)
            results["time_series_analysis"] = pattern_analysis
            
            # Add predictions if requested
            if include_predictions and len(data) >= 24:
                predictions = self.time_series_analyzer.predict_next(data, steps=6)
                results["time_series_analysis"]["predictions"] = predictions
        except Exception as e:
            logger.error(f"Time series analysis error: {e}")
            results["time_series_analysis"] = {"error": str(e)}
        
        # Step 4: Generate Summary
        results["summary"] = self._generate_summary(results, data)
        
        # Step 5: Generate Alerts
        results["alerts"] = self._generate_alerts(results)
        
        return results
    
    def _generate_summary(self, results: Dict, data: List[Dict]) -> Dict:
        """
        Generate a summary of the analysis.
        """
        # Calculate basic statistics
        download_speeds = [d.get('download_speed', 0) for d in data]
        upload_speeds = [d.get('upload_speed', 0) for d in data]
        latencies = [d.get('latency', 0) for d in data]
        
        import numpy as np
        
        # Get throttling info
        throttling_events = results.get('throttling_classification', {}).get('throttling_events', 0)
        anomaly_rate = results.get('anomaly_detection', {}).get('anomaly_rate', 0)
        
        # Determine overall status
        if throttling_events > 5 or anomaly_rate > 0.2:
            status = "critical"
            status_message = "Significant throttling detected. Consider filing a complaint."
        elif throttling_events > 0 or anomaly_rate > 0.1:
            status = "warning"
            status_message = "Some throttling patterns detected. Monitor closely."
        else:
            status = "good"
            status_message = "Network performance appears normal."
        
        return {
            "status": status,
            "status_message": status_message,
            "statistics": {
                "avg_download_speed": float(np.mean(download_speeds)) if download_speeds else 0,
                "avg_upload_speed": float(np.mean(upload_speeds)) if upload_speeds else 0,
                "avg_latency": float(np.mean(latencies)) if latencies else 0,
                "min_download_speed": float(np.min(download_speeds)) if download_speeds else 0,
                "max_download_speed": float(np.max(download_speeds)) if download_speeds else 0
            },
            "throttling_detected": throttling_events > 0,
            "throttling_events": throttling_events,
            "anomaly_rate": anomaly_rate
        }
    
    def _generate_alerts(self, results: Dict) -> List[Dict]:
        """
        Generate user alerts based on analysis.
        """
        alerts = []
        
        # Check for throttling
        throttling_events = results.get('throttling_classification', {}).get('high_confidence_events', [])
        if throttling_events:
            most_common_type = max(
                results.get('throttling_classification', {}).get('throttling_types', {}).items(),
                key=lambda x: x[1],
                default=('unknown', 0)
            )[0]
            
            alerts.append({
                "type": "throttling_detected",
                "severity": "high",
                "title": "⚠️ Possible Throttling Detected",
                "message": f"We detected {len(throttling_events)} throttling events. Most common type: {most_common_type}.",
                "action": "View detailed report and consider filing a complaint."
            })
        
        # Check for patterns
        patterns = results.get('time_series_analysis', {}).get('patterns_detected', [])
        for pattern in patterns:
            if pattern.get('severity', 0) > 0.3:
                alerts.append({
                    "type": "pattern_detected",
                    "severity": "medium",
                    "title": f"📊 {pattern.get('type', 'Pattern').replace('_', ' ').title()} Detected",
                    "message": pattern.get('description', 'A recurring pattern was detected.'),
                    "action": "Review your speed logs during affected hours."
                })
        
        # Check for high anomaly rate
        anomaly_rate = results.get('anomaly_detection', {}).get('anomaly_rate', 0)
        if anomaly_rate > 0.15:
            alerts.append({
                "type": "high_anomaly_rate",
                "severity": "medium",
                "title": "🚨 Unusual Network Behavior",
                "message": f"{anomaly_rate*100:.1f}% of your network measurements are anomalous.",
                "action": "This may indicate ISP issues or throttling."
            })
        
        return alerts
    
    def quick_check(self, record: Dict) -> Dict:
        """
        Perform a quick check on a single network measurement.
        
        Args:
            record: Single network log dictionary
            
        Returns:
            Quick analysis result
        """
        # Anomaly check
        anomaly_result = self.anomaly_detector.detect_single(record)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "is_anomaly": anomaly_result.get('is_anomaly', False),
            "anomaly_confidence": anomaly_result.get('confidence', 0),
            "download_speed": record.get('download_speed'),
            "upload_speed": record.get('upload_speed'),
            "latency": record.get('latency')
        }
        
        # If anomaly, classify it
        if result['is_anomaly']:
            classification = self.throttling_classifier.classify_single(record)
            result['throttling_type'] = classification.get('throttling_type')
            result['throttling_confidence'] = classification.get('confidence')
            result['explanation'] = self.throttling_classifier.explain_prediction(record, classification)
        
        return result
    
    def get_throttling_evidence(self, data: List[Dict]) -> Dict:
        """
        Generate evidence summary for legal reports.
        
        Args:
            data: List of network log dictionaries
            
        Returns:
            Evidence summary for legal documentation
        """
        analysis = self.analyze(data, include_predictions=False)
        
        import numpy as np
        
        download_speeds = [d.get('download_speed', 0) for d in data]
        promised_speeds = [d.get('promised_download', 100) for d in data]
        
        # Calculate compliance
        compliance_checks = [
            actual >= promised * 0.8  # 80% of promised speed
            for actual, promised in zip(download_speeds, promised_speeds)
        ]
        compliance_rate = sum(compliance_checks) / len(compliance_checks) if compliance_checks else 0
        
        evidence = {
            "analysis_period": {
                "start": data[0].get('timestamp') if data else None,
                "end": data[-1].get('timestamp') if data else None,
                "total_measurements": len(data)
            },
            "speed_statistics": {
                "average_download": float(np.mean(download_speeds)),
                "minimum_download": float(np.min(download_speeds)),
                "maximum_download": float(np.max(download_speeds)),
                "standard_deviation": float(np.std(download_speeds)),
                "promised_speed": float(np.mean(promised_speeds))
            },
            "compliance": {
                "rate": compliance_rate,
                "meets_80_percent_threshold": compliance_rate >= 0.8,
                "violations": len([c for c in compliance_checks if not c])
            },
            "throttling_evidence": {
                "events_detected": analysis.get('throttling_classification', {}).get('throttling_events', 0),
                "types_detected": analysis.get('throttling_classification', {}).get('throttling_types', {}),
                "patterns": analysis.get('time_series_analysis', {}).get('patterns_detected', [])
            },
            "ai_confidence": {
                "anomaly_detection_rate": analysis.get('anomaly_detection', {}).get('anomaly_rate', 0),
                "model_versions": {
                    "anomaly_detector": "IsolationForest v1.0",
                    "classifier": "GradientBoosting v1.0",
                    "time_series": "LSTM v1.0"
                }
            },
            "summary": analysis.get('summary', {})
        }
        
        return evidence
