import React, { useState, useRef, useEffect } from "react";
import { uploadVideo, searchPlates } from '../api';
import { 
  Box, 
  Typography, 
  Button, 
  Card,
  LinearProgress,
  Avatar,
  Alert,
  IconButton,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  CircularProgress,
  Grid,
  Stack,
  Divider
} from "@mui/material";
import { 
  CloudUpload,
  Search as SearchIcon,
  Dashboard as DashboardIcon,
  Close as CloseIcon,
  PlayCircleOutline,
  DownloadForOffline,
  DataObject
} from "@mui/icons-material";
import { styled } from "@mui/material/styles";
import api from '../api';

// Custom theme colors
const sidebarBg = '#1a2b4a';
const highlightColor = '#3a8dde';
const primaryColor = '#2a4b7c';

// Styled Components
const VisuallyHiddenInput = styled('input')({
  clip: 'rect(0 0 0 0)',
  clipPath: 'inset(50%)',
  height: 1,
  overflow: 'hidden',
  position: 'absolute',
  bottom: 0,
  left: 0,
  whiteSpace: 'nowrap',
  width: 1,
});

const UploadCard = styled(Card)(({ theme }) => ({
  maxWidth: 600,
  margin: '0 auto',
  padding: theme.spacing(4),
  borderRadius: '12px',
  boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
  border: '1px solid rgba(0,0,0,0.05)'
}));

const PreviewCard = styled(Card)(({ theme }) => ({
  maxWidth: 900,
  margin: '0 auto',
  padding: theme.spacing(4),
  borderRadius: '12px',
  boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
  border: '1px solid rgba(0,0,0,0.05)'
}));

const SearchCard = styled(Card)(({ theme }) => ({
  maxWidth: 600,
  margin: '0 auto',
  padding: theme.spacing(4),
  borderRadius: '12px',
  boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
  border: '1px solid rgba(0,0,0,0.05)'
}));

const NavButton = styled(Button)(({ active }) => ({
  justifyContent: 'flex-start',
  textTransform: 'none',
  padding: '12px 24px',
  marginBottom: '8px',
  borderRadius: '8px',
  backgroundColor: active ? primaryColor : 'transparent',
  color: active ? '#fff' : 'rgba(255,255,255,0.8)',
  fontWeight: active ? 600 : 400,
  '&:hover': {
    backgroundColor: primaryColor,
    color: '#fff'
  },
  '& .MuiButton-startIcon': {
    color: active ? '#fff' : 'rgba(255,255,255,0.8)'
  }
}));

const MetadataBox = styled(Box)({
  backgroundColor: 'rgba(0,0,0,0.03)',
  padding: '16px',
  borderRadius: '8px',
  marginTop: '16px',
});

const Dashboard = () => {
  const [activeSection, setActiveSection] = useState("upload");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [plateNumber, setPlateNumber] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState(null);
  const [searchError, setSearchError] = useState(null);
  
  // New states for the enhanced workflow
  const [uploadedVideo, setUploadedVideo] = useState(null);
  const [videoMetadata, setVideoMetadata] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingComplete, setProcessingComplete] = useState(false);
  const [processedVideoUrl, setProcessedVideoUrl] = useState(null);
  const [csvUrl, setCsvUrl] = useState(null);
  const [processingError, setProcessingError] = useState(null);
  
  // Reference for polling interval
  const pollingIntervalRef = useRef(null);
  const videoRef = useRef(null);
  
  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
  
    setUploadError(null);
    setUploadSuccess(null);
    setIsUploading(true);
    setUploadProgress(0);
    setProcessingComplete(false);
    setProcessedVideoUrl(null);
    setCsvUrl(null);
  
    try {
      // Create an object URL for the video preview
      const videoUrl = URL.createObjectURL(file);
      
      // Get video metadata
      const videoElement = document.createElement('video');
      videoElement.preload = 'metadata';
      
      videoElement.onloadedmetadata = async () => {
        const duration = videoElement.duration;
        const fps = 25; // Estimated FPS (most videos)
        const estimatedFrames = Math.round(duration * fps);
        
        // Update: Each frame takes ~8s to process
        // Assuming we're processing 1 frame per second of video (typical sampling rate)
        const frameStep = Math.round(fps); // Process 1 frame per second of video
        const processedFrameCount = Math.ceil(duration); // Number of frames to process
        const estimatedProcessingTime = processedFrameCount * 8; // 8 seconds per frame
        
        setVideoMetadata({
          name: file.name,
          size: formatFileSize(file.size),
          duration: formatDuration(duration),
          fps: fps,
          frames: estimatedFrames,
          estimatedTime: formatDuration(estimatedProcessingTime)
        });
        
        // Upload the file but don't process it yet
        try {
          const formData = new FormData();
          formData.append('video', file);
          
          const response = await api.post('/upload/no_process', formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
            onUploadProgress: (progressEvent) => {
              if (progressEvent.total) {
                const percent = Math.round(
                  (progressEvent.loaded * 100) / progressEvent.total
                );
                setUploadProgress(percent);
              }
            },
            timeout: 300000 // 5 minutes for large videos
          });
          
          setUploadedVideo({
            file: file,
            url: videoUrl,
            filename: file.name,
            ...response.data
          });
          
          setUploadSuccess({
            message: 'Video uploaded successfully! Ready to process.',
            filename: file.name
          });
          
        } catch (error) {
          setUploadError(error.message || "Upload failed");
        } finally {
          setIsUploading(false);
        }
      };
      
      videoElement.onerror = () => {
        setUploadError("Could not read video metadata. The file might be corrupted.");
        setIsUploading(false);
      };
      
      videoElement.src = videoUrl;
      
    } catch (error) {
      setUploadError(error.message || "Upload failed");
      setIsUploading(false);
    }
  };
  
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  const formatDuration = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}h ${mins}m ${secs}s`;
    } else if (mins > 0) {
      return `${mins}m ${secs}s`;
    } else {
      return `${secs}s`;
    }
  };
  
  const handleProcessVideo = async () => {
    if (!uploadedVideo) return;
    
    setProcessingError(null);
    setIsProcessing(true);
    setProcessingProgress(0);
    
    try {
      // Start the processing
      const response = await api.post(`/process/${encodeURIComponent(uploadedVideo.filename)}`);
      const taskId = response.data.task_id;
      
      // Set up polling for progress updates
      pollingIntervalRef.current = setInterval(async () => {
        try {
          const progressResponse = await api.get(`/process/status/${taskId}`);
          const status = progressResponse.data.status;
          
          if (status === 'processing') {
            setProcessingProgress(progressResponse.data.progress || 0);
          } else if (status === 'completed') {
            clearInterval(pollingIntervalRef.current);
            setProcessingProgress(100);
            setProcessingComplete(true);
            setIsProcessing(false);
            
            // Set URLs for processed video and CSV
            setProcessedVideoUrl(`${api.defaults.baseURL}/download/video/${encodeURIComponent(uploadedVideo.filename)}`);
            setCsvUrl(`${api.defaults.baseURL}/download/csv/${encodeURIComponent(uploadedVideo.filename.split('.')[0])}.csv`);
            
          } else if (status === 'failed') {
            clearInterval(pollingIntervalRef.current);
            setProcessingError(progressResponse.data.error || "Processing failed");
            setIsProcessing(false);
          }
        } catch (error) {
          console.error("Error polling for status:", error);
        }
      }, 1000); // Poll every second
      
    } catch (error) {
      setProcessingError(error.message || "Failed to start processing");
      setIsProcessing(false);
    }
  };

  const handleSearchClick = async () => {
    setSearchResults(null);
    setSearchError(null);
    
    if (!plateNumber.trim()) {
      setSearchError("Please enter a license plate number");
      return;
    }

    setIsSearching(true);
    
    try {
      // Use the searchPlates function from api.js
      const response = await searchPlates(plateNumber.trim());
      setSearchResults(response);
    } catch (error) {
      setSearchError(error.message);
    } finally {
      setIsSearching(false);
    }
  };
  
  const resetUpload = () => {
    if (uploadedVideo?.url) {
      URL.revokeObjectURL(uploadedVideo.url);
    }
    if (processedVideoUrl) {
      URL.revokeObjectURL(processedVideoUrl);
    }
    
    setUploadedVideo(null);
    setVideoMetadata(null);
    setUploadSuccess(null);
    setProcessingComplete(false);
    setProcessedVideoUrl(null);
    setCsvUrl(null);
  };

  const renderContent = () => {
    switch (activeSection) {
      case "upload":
        if (uploadedVideo && !processingComplete) {
          return renderVideoPreview();
        } else if (processingComplete) {
          return renderProcessedResults();
        } else {
          return renderUploadForm();
        }
      case "search":
        return renderSearch();
      default:
        return null;
    }
  };
  
  const renderUploadForm = () => {
    return (
      <>
        <Typography variant="h5" gutterBottom sx={{ 
          fontWeight: 600,
          color: sidebarBg,
          mb: 3
        }}>
          Upload Video for Processing
        </Typography>
        
        {uploadSuccess && (
          <Alert
            severity="success"
            action={
              <IconButton
                aria-label="close"
                color="inherit"
                size="small"
                onClick={() => setUploadSuccess(null)}
              >
                <CloseIcon fontSize="inherit" />
              </IconButton>
            }
            sx={{ 
              mb: 3,
              borderRadius: 2,
              boxShadow: 1
            }}
          >
            <Box>
              <Typography fontWeight="bold">{uploadSuccess.message}</Typography>
              <Typography variant="body2">File: {uploadSuccess.filename}</Typography>
            </Box>
          </Alert>
        )}

        <UploadCard>
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <CloudUpload sx={{ 
              fontSize: 60, 
              color: highlightColor, 
              mb: 2 
            }} />
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
              Select a video file
            </Typography>
            <Typography color="textSecondary">
              The system will automatically detect license plates in your video
            </Typography>
          </Box>
          
          <Button
            component="label"
            variant="contained"
            fullWidth
            size="large"
            startIcon={<CloudUpload />}
            disabled={isUploading}
            sx={{ 
              py: 1.5,
              backgroundColor: highlightColor,
              '&:hover': {
                backgroundColor: primaryColor
              }
            }}
          >
            Choose File
            <VisuallyHiddenInput 
              type="file" 
              accept="video/*" 
              onChange={handleFileUpload} 
            />
          </Button>
          
          {isUploading && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                Uploading... {uploadProgress}%
              </Typography>
              <LinearProgress 
                variant="determinate" 
                value={uploadProgress} 
                sx={{ 
                  height: 8, 
                  borderRadius: 4,
                  backgroundColor: 'rgba(58, 141, 222, 0.2)',
                  '& .MuiLinearProgress-bar': {
                    backgroundColor: highlightColor
                  }
                }}
              />
            </Box>
          )}

          {uploadError && (
            <Alert
              severity="error"
              sx={{ 
                mt: 2,
                borderRadius: 2
              }}
              onClose={() => setUploadError(null)}
            >
              {uploadError}
            </Alert>
          )}
        </UploadCard>
      </>
    );
  };
  
  const renderVideoPreview = () => {
    return (
      <>
        <Typography variant="h5" gutterBottom sx={{ 
          fontWeight: 600,
          color: sidebarBg,
          mb: 3
        }}>
          Video Preview
        </Typography>
        
        <PreviewCard>
          {/* Video Preview Section */}
          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <Box sx={{ position: 'relative', width: '100%', pt: '56.25%' /* 16:9 Aspect Ratio */ }}>
                <Box
                  component="video"
                  ref={videoRef}
                  controls
                  sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    borderRadius: 2,
                    bgcolor: 'black'
                  }}
                  src={uploadedVideo?.url}
                />
              </Box>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ fontWeight: 500, mb: 2 }}>
                {uploadedVideo?.filename}
              </Typography>
              
              <MetadataBox>
                <Stack spacing={2}>
                  {videoMetadata && (
                    <>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="textSecondary">File Size</Typography>
                        <Typography variant="body2" fontWeight={500}>{videoMetadata.size}</Typography>
                      </Box>
                      <Divider />
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="textSecondary">Duration</Typography>
                        <Typography variant="body2" fontWeight={500}>{videoMetadata.duration}</Typography>
                      </Box>
                      <Divider />
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="textSecondary">Frame Rate</Typography>
                        <Typography variant="body2" fontWeight={500}>{videoMetadata.fps} fps</Typography>
                      </Box>
                      <Divider />
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="textSecondary">Total Frames</Typography>
                        <Typography variant="body2" fontWeight={500}>{videoMetadata.frames}</Typography>
                      </Box>
                      <Divider />
                      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                        <Typography variant="body2" color="textSecondary">Est. Processing Time</Typography>
                        <Typography variant="body2" fontWeight={500}>{videoMetadata.estimatedTime}</Typography>
                      </Box>
                    </>
                  )}
                </Stack>
              </MetadataBox>
              
              {isProcessing ? (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="body2" color="textSecondary" gutterBottom>
                    Processing... {processingProgress}%
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={processingProgress} 
                    sx={{ 
                      height: 8, 
                      borderRadius: 4,
                      backgroundColor: 'rgba(58, 141, 222, 0.2)',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: highlightColor
                      }
                    }}
                  />
                  <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                    Detecting license plates and tracking objects...
                  </Typography>
                </Box>
              ) : (
                <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                  <Button
                    variant="contained"
                    size="large"
                    fullWidth
                    startIcon={<PlayCircleOutline />}
                    onClick={handleProcessVideo}
                    sx={{ 
                      py: 1.5,
                      backgroundColor: highlightColor,
                      '&:hover': {
                        backgroundColor: primaryColor
                      }
                    }}
                  >
                    Process Video
                  </Button>
                  
                  <Button
                    variant="outlined"
                    size="large"
                    color="inherit"
                    onClick={resetUpload}
                  >
                    Cancel
                  </Button>
                </Box>
              )}
              
              {processingError && (
                <Alert
                  severity="error"
                  sx={{ 
                    mt: 2,
                    borderRadius: 2
                  }}
                  onClose={() => setProcessingError(null)}
                >
                  {processingError}
                </Alert>
              )}
            </Grid>
          </Grid>
        </PreviewCard>
      </>
    );
  };
  
  const renderProcessedResults = () => {
    return (
      <>
        <Typography variant="h5" gutterBottom sx={{ 
          fontWeight: 600,
          color: sidebarBg,
          mb: 3
        }}>
          Processing Complete
        </Typography>
        
        <Alert
          severity="success"
          sx={{ 
            mb: 3,
            borderRadius: 2,
            boxShadow: 1
          }}
        >
          <Typography fontWeight="bold">
            License plate detection completed successfully!
          </Typography>
        </Alert>
        
        <PreviewCard>
          <Grid container spacing={4}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ fontWeight: 500, mb: 2 }}>
                Processed Video
              </Typography>
              
              <Box sx={{ 
                p: 3, 
                textAlign: 'center',
                bgcolor: 'rgba(0,0,0,0.03)', 
                borderRadius: 2,
                height: '200px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                mb: 2
              }}>
                <DownloadForOffline sx={{ fontSize: 60, color: highlightColor, mb: 2 }} />
                <Typography>
                  Processed video ready for download
                </Typography>
              </Box>
              
              <Button
                variant="contained"
                fullWidth
                startIcon={<DownloadForOffline />}
                href={processedVideoUrl}
                download={`processed_${uploadedVideo?.filename || 'video'}`}
                target="_blank"
                sx={{ 
                  backgroundColor: highlightColor,
                  '&:hover': {
                    backgroundColor: primaryColor
                  }
                }}
              >
                Download Processed Video
              </Button>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Typography variant="h6" sx={{ fontWeight: 500, mb: 2 }}>
                Detection Results
              </Typography>
              
              <Box sx={{ 
                p: 3, 
                textAlign: 'center',
                bgcolor: 'rgba(0,0,0,0.03)', 
                borderRadius: 2,
                height: '200px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                mb: 2
              }}>
                <DataObject sx={{ fontSize: 60, color: '#4caf50', mb: 2 }} />
                <Typography>
                  Detection results ready for download
                </Typography>
                <Typography variant="caption" color="textSecondary" sx={{ mt: 1 }}>
                  CSV file with plate number, timestamp and video information
                </Typography>
              </Box>
              
              <Button
                variant="contained"
                fullWidth
                startIcon={<DataObject />}
                href={csvUrl}
                download={`results_${uploadedVideo?.filename?.split('.')[0] || 'data'}.csv`}
                target="_blank"
                sx={{ 
                  mb: 2,
                  backgroundColor: '#4caf50',
                  '&:hover': {
                    backgroundColor: '#388e3c'
                  }
                }}
              >
                Download CSV Results
              </Button>
              
              <Button
                variant="outlined"
                fullWidth
                onClick={resetUpload}
              >
                Upload Another Video
              </Button>
            </Grid>
          </Grid>
        </PreviewCard>
      </>
    );
  };
  
  const renderSearch = () => {
    return (
      <>
        <Typography variant="h5" gutterBottom sx={{ 
          fontWeight: 600,
          color: sidebarBg,
          mb: 3
        }}>
          Search License Plate
        </Typography>
        
        <SearchCard>
          <Box sx={{ textAlign: 'center', mb: 3 }}>
            <SearchIcon sx={{ 
              fontSize: 60, 
              color: highlightColor, 
              mb: 2 
            }} />
            <Typography variant="h6" gutterBottom sx={{ fontWeight: 500 }}>
              Enter License Plate Number
            </Typography>
            <Typography color="textSecondary">
              Search for a specific license plate in processed videos
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            <TextField
              fullWidth
              label="License Plate Number"
              variant="outlined"
              value={plateNumber}
              onChange={(e) => setPlateNumber(e.target.value)}
              disabled={isSearching}
              error={!!searchError}
              helperText={searchError}
            />
            <Button
              variant="contained"
              size="large"
              startIcon={<SearchIcon />}
              onClick={handleSearchClick}
              disabled={isSearching || !plateNumber.trim()}
              sx={{ 
                py: 1.5,
                backgroundColor: highlightColor,
                '&:hover': {
                  backgroundColor: primaryColor
                }
              }}
            >
              {isSearching ? "Searching..." : "Search"}
            </Button>
          </Box>

          {isSearching && (
            <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {searchResults && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Search Results
              </Typography>
              
              {searchResults.results.length > 0 ? (
                <TableContainer component={Paper}>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Video</TableCell>
                        <TableCell>Timestamp</TableCell>
                        <TableCell>Action</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {searchResults.results.map((result, index) => (
                        <TableRow key={index}>
                          <TableCell>{result.video}</TableCell>
                          <TableCell>{result.timestamp} seconds</TableCell>
                          <TableCell>
                            <Button 
                              startIcon={<PlayCircleOutline />}
                              size="small"
                              href={`${api.defaults.baseURL}/download/video/${encodeURIComponent(result.video)}#t=${result.timestamp}`}
                              target="_blank"
                            >
                              View
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info" sx={{ mt: 2 }}>
                  No matching plates found
                </Alert>
              )}
            </Box>
          )}
        </SearchCard>
      </>
    );
  };

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Box sx={{ 
        width: 280,
        backgroundColor: sidebarBg,
        color: 'white',
        padding: 2,
        display: 'flex',
        flexDirection: 'column'
      }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 4, pl: 1 }}>
          <Avatar sx={{ 
            bgcolor: highlightColor, 
            mr: 2,
            width: 40,
            height: 40
          }}>
            <DashboardIcon />
          </Avatar>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>RoadScan</Typography>
        </Box>

        <Box sx={{ flex: 1 }}>
          <NavButton
            fullWidth
            startIcon={<CloudUpload />}
            onClick={() => setActiveSection("upload")}
            active={activeSection === "upload"}
          >
            Upload Video
          </NavButton>
          
          <NavButton
            fullWidth
            startIcon={<SearchIcon />}
            onClick={() => setActiveSection("search")}
            active={activeSection === "search"}
          >
            Search Plate
          </NavButton>
        </Box>
      </Box>

      {/* Main Content */}
      <Box sx={{ 
        flex: 1,
        padding: 4,
        backgroundColor: '#f5f7fa',
        overflowY: 'auto'
      }}>
        <Box sx={{ maxWidth: processingComplete ? 1200 : 900, mx: 'auto' }}>
          {renderContent()}
        </Box>
      </Box>
    </Box>
  );
};

export default Dashboard;