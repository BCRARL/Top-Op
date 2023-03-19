import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib import colors

from DataSaver import *



def flipLoadConditions(formattedArray):
    """
    Takes the formatted Array and returns three variations with the circles fliped horizontally, vertically, and over the diagonal.

    Parameters:
        - formattedArray
    
    returns:
        - formatted LR: fliped left right(horizontal mirror)
        - formatted UD: fliped up down(vertical mirror)
        - formatted diagnal: fliped over both horizontal and vertical
    """
    circles = formattedArray[0]
    radii = formattedArray[1]
    forces = formattedArray[2]
    nelx, nely = formattedArray[3], formattedArray[4]
    Y, C_max, S_max = formattedArray[5], formattedArray[6], formattedArray[7]

    #create arrays for circle positions
    circlesLR = circles.copy()
    circlesUD = circles.copy()
    circlesDiagonal = circles.copy()

    #flip the x positions
    circlesLR[0,:] = 2-circlesLR[0,:]

    #flip y postions
    circlesUD[1,:] = 1-circlesUD[1,:]

    #flip diagonal
    circlesDiagonal[0,:] = circlesLR[0,:]
    circlesDiagonal[1,:] = circlesUD[1,:]

    forcesLR = forces.copy()
    forcesUD = forces.copy()
    forcesDiagonal = forces.copy()

    #flip the x magnitude
    forcesLR[0,:] = -forcesLR[0,:]

    #flip y magnitude
    forcesUD[1,:] = -forcesUD[1,:]

    #flip diagonal
    forcesDiagonal[0,:] = forcesLR[0,:]
    forcesDiagonal[1,:] = forcesUD[1,:]

    #duplicate
    formattedLR = [circlesLR,radii,forcesLR,nelx,nely,Y,C_max,S_max]
    formattedUD = [circlesUD,radii,forcesUD,nelx,nely,Y,C_max,S_max]
    formattedDiagonal = [circlesDiagonal,radii,forcesDiagonal,nelx,nely,Y,C_max,S_max]

    return formattedLR,formattedUD,formattedDiagonal

def AugmentData_mirrorPart(agentFileToGet):
    formated,x_array,derivatives_array,objectives_array,mark = getData(agentFileToGet)
    nelx, nely = formated[3], formated[4]
    print(x_array[0].shape)
    print(derivatives_array[0].shape)


    formattedLR,formattedUD,formattedDiagonal = flipLoadConditions(formated)


    x_array_mirrored = []
    derivatives_array_mirrored = []
    for x,derivative in zip(x_array,derivatives_array):
        #print(x.shape,derivative.shape)
        x = np.reshape(x,(nelx+1,nely+1),order= 'F')
        x = np.fliplr(x)
        x_array_mirrored.append(np.ravel(x,order='F'))
        derivative = np.reshape(derivative,(nelx+1,nely+1),order= 'F')
        derivative = np.fliplr(derivative)
        derivatives_array_mirrored.append(np.ravel(derivative,order='F'))
    if(len(mark) == 0):
        saveAugmentedData(formattedLR,x_array_mirrored,objectives_array,derivatives_array_mirrored,"MirroredLR")
    else:
        saveAugmentedData(formattedLR,x_array_mirrored,objectives_array,derivatives_array_mirrored,"MirroredLR_{}".format(mark))

    x_array_mirrored = []
    derivatives_array_mirrored = []
    for x,derivative in zip(x_array,derivatives_array):
        x = np.reshape(x,(nelx+1,nely+1),order= 'F')
        x = np.flipud(x)
        x_array_mirrored.append(np.ravel(x,order='F'))
        derivative = np.reshape(derivative,(nelx+1,nely+1),order= 'F')
        derivative = np.flipud(derivative)
        derivatives_array_mirrored.append(np.ravel(derivative,order='F'))
    if(len(mark) == 0):
        saveAugmentedData(formattedUD,x_array_mirrored,objectives_array,derivatives_array_mirrored,"MirroredUD")
    else:
        saveAugmentedData(formattedUD,x_array_mirrored,objectives_array,derivatives_array_mirrored,"MirroredUD_{}".format(mark))

    x_array_mirrored = []
    derivatives_array_mirrored = []
    for x,derivative in zip(x_array,derivatives_array):
        x = np.reshape(x,(nelx+1,nely+1),order= 'F')
        x = np.fliplr(x)
        x = np.flipud(x)
        x_array_mirrored.append(np.ravel(x,order='F'))
        derivative = np.reshape(derivative,(nelx+1,nely+1),order= 'F')
        derivative = np.fliplr(derivative)
        derivative = np.flipud(derivative)
        derivatives_array_mirrored.append(np.ravel(derivative,order='F'))
    if(len(mark) == 0):
        saveAugmentedData(formattedDiagonal,x_array_mirrored,objectives_array,derivatives_array_mirrored,"MirroredDiagonal")
    else:
        saveAugmentedData(formattedDiagonal,x_array_mirrored,objectives_array,derivatives_array_mirrored,"MirroredDiagonal_{}".format(mark))
    

def getPadding(lastIteration,nelx,nely):
    cutOff = 0.05
    lastIteration = np.where(lastIteration >= cutOff,1,0)

    im = np.reshape(lastIteration,(nelx,nely),order='F')

    #get padding on left
    lPad = 0
    for x in range(0,nelx,1):
        currentCol = im[x,:]
        avgVal = np.mean(currentCol)
        if(avgVal == 0):
            lPad += 1
        else:
            break
        
    print(lPad)
    rPad = 0
    for x in range(nelx-1,-1,-1):
        currentCol = im[x,:]
        avgVal = np.mean(currentCol)
        if(avgVal == 0):
            rPad += 1
        else:
            break
    print(rPad)

    uPad = 0
    for y in range(0,nely,1):
        currentRow = im[:,y]
        avgVal = np.mean(currentRow)
        if(avgVal == 0):
            uPad += 1
        else:
            break
    print(uPad)

    dPad = 0
    for y in range(nely-1,-1,-1):
        currentRow = im[:,y]
        avgVal = np.mean(currentRow)
        if(avgVal == 0):
            dPad += 1
        else:
            break
    print(dPad)

    return lPad,rPad,uPad,dPad

def averageArray(ar1):
    n = ar1.shape[0]
    newArray = np.zeros(n)
    #print(n)

    for i in range(n):
        if (i == 0):
            a1 = ar1[i]
            a2 = ar1[i+1]
            a3 = 0
        elif(i==n-1):
            a1 = ar1[i]
            a2 = ar1[i-1]
            a3 = 0
        else:
            a1 = ar1[i-1]
            a2 = ar1[i]
            a3 = ar1[i+1]
        
        v = (a1+a2+a3)/3
        newArray[i] = v

    return newArray

def shiftImage(image,shiftLR,shiftUD):

    if(shiftLR < 0):
        while(shiftLR < 0):
            shiftLR += 1
            colToRepeat = image[:,0]
            #shift over image
            image = np.roll(image,-1,0)
            image[:,0] = averageArray(colToRepeat)
    elif(shiftLR > 0):
        while(shiftLR > 0):
            shiftLR -= 1
            colToRepeat = image[:,-1]
            #shift over image
            image = np.roll(image,1,0)
            image[:,-1] = averageArray(colToRepeat)
    
    if(shiftUD < 0):
        while(shiftUD < 0):
            shiftUD += 1
            rowToRepeat = image[0,:]
            #shift over image
            image = np.roll(image,-1,1)
            image[0,:] = averageArray(rowToRepeat)
    elif(shiftUD > 0):
        while(shiftUD > 0):
            shiftUD -= 1
            rowToRepeat = image[-1,:]
            #shift over image
            image = np.roll(image,1,1)
            image[-1,:] = averageArray(rowToRepeat)


    return image

def getShiftAmount(iterationsArray,nelx,nely):
    """
    Takes a part and randomly translates the part to a new location preserving scale

    Works by checking how much space is left on the part of the final iteration and uses this to create a range that the part can move

    With this shift amount we can shift the part over. 
    when dealing with edge cases, we can shift elements out easily and when shifting elements in we simply repeat the edge.

    This will cause some artifacts but it may be ok with the iterateive model.
    """
    lastIteration = iterationsArray[-1]

    lPad,rPad,uPad,dPad = getPadding(lastIteration,nelx,nely)
    if(lPad == 0 and rPad == 0):
        shiftAmountLR = 0
    else:
        shiftAmountLR = np.random.randint(-lPad , rPad )

    if(uPad == 0 and rPad == 0):
        shiftAmountUD = 0
    else:
        shiftAmountUD = np.random.randint(-uPad , dPad )

    return shiftAmountLR,shiftAmountUD

def shiftLoadConditions(formatted,shiftAmountLR,shiftAmountUD):

    circles = formatted[0]
    radii = formatted[1]
    forces = formatted[2]
    nelx, nely = formatted[3], formatted[4]
    Y, C_max, S_max = formatted[5], formatted[6], formatted[7]

    x_shiftAmount = 2/nelx
    y_shiftAmount = 1/nely

    for i in range(3):
       circles[0][i] += shiftAmountLR*x_shiftAmount 
       circles[1][i] += shiftAmountUD*y_shiftAmount
    
    shiftedFormat = [circles,radii,forces,nelx,nely,Y,C_max,S_max]
    #showShiftedPart(iterationsArray,nelx+1,nely+1,shiftAmountLR,shiftAmountUD)
    return shiftedFormat

def AugmentData_shiftPart(agentFileToGet):
    formated,x_array,derivatives_array,objectives_array,mark = getData(agentFileToGet)
    nelx, nely = formated[3], formated[4]

    
    shiftLR,shiftUD = getShiftAmount(x_array,nelx+1,nely+1)
    if(shiftLR == 0 and shiftUD == 0):
        return 
    shiftedLoadConditions = shiftLoadConditions(formated,shiftLR,shiftUD)


    x_array_shifted = []
    derivatives_array_shifted = []
    for x,derivative in zip(x_array,derivatives_array):
        x = np.reshape(x,(nelx+1,nely+1),order= 'F')
        x = shiftImage(x,shiftLR,shiftUD)
        x_array_shifted.append(np.ravel(x,order='F'))
        derivative = np.reshape(derivative,(nelx+1,nely+1),order= 'F')
        derivative = shiftImage(derivative,shiftLR,shiftUD)
        derivatives_array_shifted.append(derivative)
    if(len(mark) == 0):
        saveAugmentedData(shiftedLoadConditions,x_array_shifted,objectives_array,derivatives_array_shifted,"Shifted_{}_{}".format(shiftLR,shiftUD))
    else:
        saveAugmentedData(shiftedLoadConditions,x_array_shifted,objectives_array,derivatives_array_shifted,"Shifted_{}_{}_{}".format(shiftLR,shiftUD,mark))


def showShiftedPart(iterationsArray,nelx,nely,shiftAmountLR,shiftAmountUD):
    im_array = []
    for i in range(len(iterationsArray)):
        
        print(i)
        image = np.reshape(iterationsArray[i],(nelx,nely),order='F')
        im_array.append(shiftImage(image,shiftAmountLR,shiftAmountUD))

        #print(size)   
        #show(im) 
    imagesToShow = 7
    numImages = len(im_array)
    fig,ax = plt.subplots(imagesToShow)

def CreateCircles(circleArray,radii,res:int=100):
    #fig, ax = plt.subplots(1,1)
    x= np.linspace(0,2,res)
    y = np.linspace(0,1,res//2)
    X,Y = np.meshgrid(x,y)
    l1 = 1
    def dist(num):#[x1,y1,r1,f1,a1
        return np.sqrt((circleArray[0][num]-X)**2 + (circleArray[1][num]-Y)**2) - radii[num]
    Z1 = np.minimum(dist(0),np.minimum(dist(1),dist(2)))
    #Z1 = dist(c1)

    Z1 = np.where(Z1>0,1,Z1)
    Z1 = np.where(Z1<=0,-1,Z1)

    print(Z1.shape)
    return Z1
    
def test():
    dataDirectory = r"E:\TopoptGAfileSaves\Mass minimization"
    #dataDirectory = os.getcwd()
    DATA_FILE_PATH = os.path.join(dataDirectory,'correctFOrmat')

    dir_list = os.listdir(DATA_FILE_PATH)
    max_data_points = len(dir_list)
    print("Number of data points: {}".format(len(dir_list)))

    i=np.random.randint(0,max_data_points-1)
    print(i)
    path = os.path.join(DATA_FILE_PATH,dir_list[i])
    
    AugmentData_mirrorPart(path)
    AugmentData_shiftPart(path)

def showAugmentedFiles():
    path = os.path.join(os.getcwd(),'Agents','100_50')
    filesToGet = os.listdir(path)
    numberOfFiles = len(filesToGet)

    fig,ax = plt.subplots(numberOfFiles,3)

    for i,fileName in enumerate(filesToGet):
        formated,x_array,derivatives_array,objectives_array,mark = getData(os.path.join(path,fileName))
        ax[i,0].imshow(np.reshape(x_array[-1],(101,51),order='F').T)
        ax[i,1].imshow(np.reshape(derivatives_array[-1],(101,51),order='F').T)
        ax[i,2].imshow(CreateCircles(formated[0],formated[1]))
    plt.show()

def Augment_mirror_AllData(pathToData):
    filesToGet = os.listdir(pathToData)

    for fileName in filesToGet:
        path = os.path.join(pathToData,fileName)
        AugmentData_mirrorPart(path)

def Augment_shift_AllData(pathToData,shiftTries:int = 4):
    filesToGet = os.listdir(pathToData)

    for fileName in filesToGet:
        path = os.path.join(pathToData,fileName)
        for i in range(shiftTries):
            AugmentData_shiftPart(path)

    
if (__name__ == "__main__"):
    path = os.path.join(os.getcwd(),'Agents','100_50')#I moving your true data to a new folder and then changing this path to that new folder so we can keep track of augmented data.
    
    Augment_shift_AllData(path,4)
    Augment_mirror_AllData(path)

